import mimetypes
import os
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse, FileResponse, JsonResponse
from django.core.cache import cache
from django.db.models import F
from django.db.models import Count
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.base import File
from .models import FileDrop

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024 # 2GB
MAX_PIN_ATTEMPTS = 5
PIN_LOCKOUT_SECONDS = 900
MAX_UPLOADS_PER_HOUR = 10
MAX_UPLOAD_BYTES_PER_HOUR = 5 * 1024 * 1024 * 1024  # 5 GB per IP per hour
MAX_CONTACT_PER_HOUR = 3

BLOCKED_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.sh', '.msi', '.com', '.scr', '.pif',
    '.vbs', '.vbe', '.wsf', '.wsh', '.ps1', '.ps2', '.reg', '.dll',
    '.sys', '.drv', '.hta', '.jar',
}

def _fmt_size(b):
    if b < 1024: return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.2f} MB"

def _is_previewable_image(filename):
    return os.path.splitext(filename.lower())[1] in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

def _delete_expired(drop):
    if drop.file and os.path.exists(drop.file.path):
        os.remove(drop.file.path)
    drop.delete()

def _get_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '0.0.0.0')

def _check_pin_rate_limit(ip):
    if cache.get(f'pin_lockout_{ip}'):
        return True, '🔒 Too many failed attempts. Try again in 15 minutes.'
    return False, None

def _record_failed_pin(ip):
    attempt_key = f'pin_attempts_{ip}'
    lockout_key = f'pin_lockout_{ip}'
    attempts = cache.get(attempt_key, 0) + 1
    if attempts >= MAX_PIN_ATTEMPTS:
        cache.set(lockout_key, True, PIN_LOCKOUT_SECONDS)
        cache.delete(attempt_key)
        return '🔒 Too many failed attempts. You are locked out for 15 minutes.'
    cache.set(attempt_key, attempts, PIN_LOCKOUT_SECONDS)
    remaining = MAX_PIN_ATTEMPTS - attempts
    return f"Invalid PIN. {remaining} attempt{'s' if remaining != 1 else ''} remaining before lockout."

def _file_info_from_drop(drop):
    remaining_ms = int((drop.get_expiry() - timezone.now()).total_seconds() * 1000)
    name = drop.original_filename or os.path.basename(drop.file.name)
    return {
        'pin': drop.pin,
        'name': name,
        'size': _fmt_size(drop.file.size),
        'expires_ms': remaining_ms,
        'one_time': drop.one_time,
        'has_password': bool(drop.password),
        'download_count': drop.download_count,
        'previewable': _is_previewable_image(name),
    }

def home_view(request):
    drops = list(FileDrop.objects.all())
    stats = FileDrop.objects.aggregate(total_files=Count('id'))
    active_count = sum(1 for drop in drops if not drop.is_expired())
    total_bytes = sum(drop.file.size for drop in drops if drop.file)
    return render(request, 'drop/home.html', {
        'stats': {
            'active_files': active_count,
            'total_files': stats['total_files'] or 0,
            'total_shared': _fmt_size(total_bytes),
        }
    })

def privacy_view(request):
    return render(request, 'drop/privacy.html')

def terms_view(request):
    return render(request, 'drop/terms.html')

def dmca_view(request):
    return render(request, 'drop/dmca.html')

def success_view(request, pin):
    drop = get_object_or_404(FileDrop, pin=pin)
    if drop.is_expired():
        _delete_expired(drop)
        return redirect('upload')
    return render(request, 'drop/success.html', {
        'pin': drop.pin,
        'filename': drop.original_filename or os.path.basename(drop.file.name),
        'share_url': request.build_absolute_uri(f'/get/{drop.pin}/'),
        'expires_hours': drop.expires_hours,
        'one_time': drop.one_time,
    })

def contact_view(request):
    sent = False
    error = None
    if request.method == 'POST':
        ip = _get_ip(request)
        contact_key = f'contact_{ip}'
        count = cache.get(contact_key, 0)
        if count >= MAX_CONTACT_PER_HOUR:
            error = 'Too many messages from your IP. Please wait before sending again.'
        else:
            subject_type = request.POST.get('subject', 'General')
            message = request.POST.get('message', '').strip()
            reply_email = request.POST.get('email', '').strip()
            if message:
                full_msg = f"Reply to: {reply_email or 'not provided'}\n\n{message}"
                send_mail(
                    subject=f'[SpiddyWeb] {subject_type}',
                    message=full_msg,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                cache.set(contact_key, count + 1, 3600)
                sent = True
    return render(request, 'drop/contact.html', {'sent': sent, 'error': error})

def upload_view(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        if not request.FILES.get('file'):
            if is_ajax: return JsonResponse({'status': 'error', 'message': 'No file selected.'})
            return render(request, 'drop/upload.html')

        ip = _get_ip(request)
        upload_key = f'uploads_{ip}'
        size_key = f'upload_bytes_{ip}'
        uploads = cache.get(upload_key, 0)
        upload_bytes = cache.get(size_key, 0)

        # We only rate limit the initiation of an upload (chunk_index == 0) to avoid limiting individual chunks
        chunk_index = int(request.POST.get('chunk_index', 0))
        total_chunks = int(request.POST.get('total_chunks', 1))
        upload_id = request.POST.get('upload_id', '')

        if chunk_index == 0 and uploads >= MAX_UPLOADS_PER_HOUR:
            msg = 'Upload limit reached. Max 10 uploads per hour.'
            if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
            return render(request, 'drop/upload.html', {'error': msg})

        if chunk_index == 0 and upload_bytes >= MAX_UPLOAD_BYTES_PER_HOUR:
            msg = 'Hourly data limit reached. Max 5 GB per hour.'
            if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
            return render(request, 'drop/upload.html', {'error': msg})

        uploaded_file = request.FILES['file']
        filename = request.POST.get('filename', uploaded_file.name)
        
        # Check extensions early
        ext = os.path.splitext(filename)[1].lower()
        if ext in BLOCKED_EXTENSIONS:
            msg = f'File type "{ext}" is not allowed for security reasons.'
            if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
            return render(request, 'drop/upload.html', {'error': msg})

        # Append chunk to temporary file
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Security: sanitize upload_id
        safe_upload_id = "".join(c for c in upload_id if c.isalnum())
        if not safe_upload_id:
            return JsonResponse({'status': 'error', 'message': 'Invalid upload ID.'})
            
        temp_path = os.path.join(temp_dir, f"{safe_upload_id}.part")
        
        # Write chunk
        with open(temp_path, 'ab') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
                
        # Check size limit so far
        if os.path.getsize(temp_path) > MAX_FILE_SIZE:
            os.remove(temp_path)
            return JsonResponse({'status': 'error', 'message': 'File exceeds 2GB limit.'})

        # If it's the last chunk, finalize the file
        if chunk_index == total_chunks - 1:
            try:
                expires_hours = int(request.POST.get('expires_hours', 24))
            except (ValueError, TypeError):
                expires_hours = 24
            if expires_hours not in (1, 6, 24, 168):
                expires_hours = 24
            one_time = request.POST.get('one_time') == 'true' or request.POST.get('one_time') == 'on'
            raw_password = request.POST.get('password', '').strip()

            drop = FileDrop(
                original_filename=filename,
                expires_hours=expires_hours,
                one_time=one_time,
            )
            drop.set_password(raw_password)
            
            with open(temp_path, 'rb') as f:
                drop.file.save(filename, File(f), save=True)
                
            os.remove(temp_path)
            cache.set(upload_key, uploads + 1, 3600)
            cache.set(size_key, upload_bytes + drop.file.size, 3600)
            share_url = request.build_absolute_uri(f'/get/{drop.pin}/')

            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'pin': drop.pin,
                    'filename': filename,
                    'share_url': share_url,
                    'expires_hours': expires_hours,
                    'one_time': one_time,
                    'redirect_url': f'/upload/success/{drop.pin}/',
                })
            return redirect('upload_success', pin=drop.pin)
        
        # Acknowledge successful chunk
        return JsonResponse({'status': 'chunk_success'})
        
    return render(request, 'drop/upload.html')

def get_file_view(request, pin):
    """Direct share link — shows file info without requiring PIN entry."""
    ip = _get_ip(request)
    locked, msg = _check_pin_rate_limit(ip)
    if locked:
        return render(request, 'drop/download.html', {'error': msg})
    try:
        drop = FileDrop.objects.get(pin=pin)
        if drop.is_expired():
            _delete_expired(drop)
            return render(request, 'drop/download.html', {'error': 'This link has expired.'})
        if drop.one_time and drop.download_count >= 1:
            return render(request, 'drop/download.html', {'error': 'This file was a one-time download and has already been retrieved.'})
        return render(request, 'drop/download.html', {'file_info': _file_info_from_drop(drop)})
    except FileDrop.DoesNotExist:
        _record_failed_pin(ip)
        return render(request, 'drop/download.html', {'error': 'Invalid link. File does not exist.'})

def file_preview_view(request, pin):
    drop = get_object_or_404(FileDrop, pin=pin)
    if drop.is_expired():
        _delete_expired(drop)
        return HttpResponse('Expired', status=410)
    filename = drop.original_filename or os.path.basename(drop.file.name)
    if not _is_previewable_image(filename):
        return HttpResponse('Preview not available', status=415)
    content_type, _ = mimetypes.guess_type(filename)
    return FileResponse(drop.file.open('rb'), content_type=content_type or 'application/octet-stream')

def download_view(request):
    error = None
    file_info = None
    if request.method == 'POST':
        ip = _get_ip(request)
        locked, msg = _check_pin_rate_limit(ip)
        if locked:
            return render(request, 'drop/download.html', {'error': msg})
        pin = request.POST.get('pin', '').strip()
        pwd = request.POST.get('password', '').strip()
        try:
            drop = FileDrop.objects.get(pin=pin)
            if drop.is_expired():
                _delete_expired(drop)
                error = 'This PIN has expired.'
            elif drop.one_time and drop.download_count >= 1:
                error = 'This file was a one-time download and has already been retrieved.'
            elif drop.password and not drop.verify_password(pwd):
                error = '🔒 Incorrect password for this drop.'
                file_info = _file_info_from_drop(drop)
                file_info['password_required'] = True
            else:
                cache.delete(f'pin_attempts_{ip}')
                file_info = _file_info_from_drop(drop)
        except FileDrop.DoesNotExist:
            error = _record_failed_pin(ip)
    return render(request, 'drop/download.html', {'error': error, 'file_info': file_info})

def file_download_view(request, pin):
    """Serves the actual file bytes; called by JS fetch for progress tracking."""
    ip = _get_ip(request)
    locked, _ = _check_pin_rate_limit(ip)
    if locked:
        return HttpResponse('Too many requests', status=429)
    try:
        drop = FileDrop.objects.get(pin=pin)
        if drop.is_expired():
            _delete_expired(drop)
            return HttpResponse('Expired', status=410)
        if drop.one_time and drop.download_count >= 1:
            return HttpResponse('Already downloaded', status=410)
        
        # Verify password if required
        pwd = request.GET.get('password', '') or request.POST.get('password', '')
        if drop.password and not drop.verify_password(pwd):
            return HttpResponse('Password required or invalid', status=403)

        filename = drop.original_filename or os.path.basename(drop.file.name)
        content_type, _ = mimetypes.guess_type(filename)
        if drop.one_time:
            with drop.file.open('rb') as file_handle:
                payload = file_handle.read()
            FileDrop.objects.filter(pk=drop.pk).update(download_count=F('download_count') + 1)
            response = HttpResponse(payload, content_type=content_type or 'application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = str(len(payload))
            _delete_expired(drop)
            return response
        FileDrop.objects.filter(pk=drop.pk).update(download_count=F('download_count') + 1)
        return FileResponse(drop.file.open('rb'), as_attachment=True, filename=filename)
    except FileDrop.DoesNotExist:
        _record_failed_pin(ip)
        return HttpResponse('Not found', status=404)

def hq_view(request):
    """Spidey HQ Admin Dashboard"""
    drops = list(FileDrop.objects.all())
    now = timezone.now()
    active_drops = [d for d in drops if not d.is_expired()]
    expired_drops = [d for d in drops if d.is_expired()]
    
    # Action: Manual Purge
    purged_count = 0
    if request.method == 'POST' and request.POST.get('action') == 'purge':
        for exp in expired_drops:
            _delete_expired(exp)
            purged_count += 1
        return redirect('hq')

    total_bytes = sum(d.file.size for d in drops if d.file)
    active_bytes = sum(d.file.size for d in active_drops if d.file)
    
    # Extension breakdown
    ext_counts = {}
    for d in active_drops:
        ext = os.path.splitext(d.original_filename or d.file.name)[1].lower() or 'no ext'
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    return render(request, 'drop/hq.html', {
        'total_drops': len(drops),
        'active_drops_count': len(active_drops),
        'expired_drops_count': len(expired_drops),
        'total_storage_fmt': _fmt_size(total_bytes),
        'active_storage_fmt': _fmt_size(active_bytes),
        'active_drops': active_drops[:20], # top 20
        'ext_counts': ext_counts,
        'purged_count': purged_count,
    })

def docs_view(request):
    """SpiddyWeb Interactive Documentation & API Guide"""
    return render(request, 'drop/docs.html')

def custom_404_view(request, exception=None):
    """Spidey Custom 404 Multiverse Error Page"""
    return render(request, 'drop/404.html', status=404)

def robots_txt_view(request):
    """SEO Robots.txt handler"""
    content = """User-agent: *
Allow: /
Disallow: /hq/

Sitemap: https://spiddy-web.vercel.app/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")

def sitemap_xml_view(request):
    """SEO Dynamic Sitemap.xml handler"""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://spiddy-web.vercel.app/</loc>
    <priority>1.0</priority>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/upload/</loc>
    <priority>0.9</priority>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/receive/</loc>
    <priority>0.8</priority>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/docs/</loc>
    <priority>0.7</priority>
    <changefreq>weekly</changefreq>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/privacy/</loc>
    <priority>0.5</priority>
    <changefreq>monthly</changefreq>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/terms/</loc>
    <priority>0.5</priority>
    <changefreq>monthly</changefreq>
  </url>
  <url>
    <loc>https://spiddy-web.vercel.app/contact/</loc>
    <priority>0.5</priority>
    <changefreq>monthly</changefreq>
  </url>
</urlset>
"""
    return HttpResponse(content, content_type="application/xml")

# --- SPIDER-VERSE ROOMS VIEWS ---

from .models import Room, RoomMessage
import json

def create_room_view(request):
    if request.method == 'POST':
        sender_name = request.POST.get('sender_name', '').strip()
        if not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Name is required'})
        
        # Create a new Room
        room = Room.objects.create()
        
        # Save credentials in session
        request.session['room_code'] = room.code
        request.session['sender_name'] = sender_name
        
        # Create a system message welcoming the user
        RoomMessage.objects.create(
            room=room,
            sender_name='System (K.A.R.E.N)',
            text_content=f"{sender_name} has created the web room! Share the code {room.code} with your friends."
        )
        
        return JsonResponse({'status': 'success', 'room_code': room.code})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def join_room_view(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        sender_name = request.POST.get('sender_name', '').strip()
        
        if not room_code or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Room code and Name are required'})
        
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid Room Code'})
            
        if room.is_expired():
            room.delete()
            return JsonResponse({'status': 'error', 'message': 'This room has self-destructed.'})
            
        request.session['room_code'] = room.code
        request.session['sender_name'] = sender_name
        
        RoomMessage.objects.create(
            room=room,
            sender_name='System (K.A.R.E.N)',
            text_content=f"{sender_name} just swung into the room!"
        )
        
        return JsonResponse({'status': 'success', 'room_code': room.code})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def room_chat_view(request, room_code):
    try:
        room = Room.objects.get(code=room_code)
    except Room.DoesNotExist:
        return render(request, 'drop/404.html', status=404)
        
    if room.is_expired():
        room.delete()
        return render(request, 'drop/download.html', {'error': 'This room has self-destructed.'})
        
    session_code = request.session.get('room_code')
    sender_name = request.session.get('sender_name')
    
    # If not authenticated for this room, redirect to home
    if session_code != room_code or not sender_name:
        return redirect('home')
        
    return render(request, 'drop/room.html', {
        'room': room,
        'sender_name': sender_name
    })

def api_send_message(request, room_code):
    if request.method == 'POST':
        session_code = request.session.get('room_code')
        sender_name = request.session.get('sender_name')
        
        if session_code != room_code or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            
        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Room not found'}, status=404)
            
        text_content = request.POST.get('text_content', '').strip()
        uploaded_file = request.FILES.get('file')
        
        if not text_content and not uploaded_file:
            return JsonResponse({'status': 'error', 'message': 'Cannot send empty message'})
            
        original_filename = None
        if uploaded_file:
            original_filename = uploaded_file.name
            
        RoomMessage.objects.create(
            room=room,
            sender_name=sender_name,
            text_content=text_content,
            file=uploaded_file,
            original_filename=original_filename
        )
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def api_get_messages(request, room_code):
    if request.method == 'GET':
        session_code = request.session.get('room_code')
        sender_name = request.session.get('sender_name')
        
        if session_code != room_code or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            
        last_id = request.GET.get('last_id', 0)
        try:
            last_id = int(last_id)
        except ValueError:
            last_id = 0
            
        messages = RoomMessage.objects.filter(room__code=room_code, id__gt=last_id).order_by('id')
        
        data = []
        for msg in messages:
            file_url = msg.file.url if msg.file else None
            data.append({
                'id': msg.id,
                'sender_name': msg.sender_name,
                'text_content': msg.text_content,
                'file_url': file_url,
                'original_filename': msg.original_filename,
                'created_at': msg.created_at.strftime("%I:%M %p"),
                'is_me': msg.sender_name == sender_name,
                'is_system': msg.sender_name == 'System (K.A.R.E.N)'
            })
            
        return JsonResponse({'status': 'success', 'messages': data})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
