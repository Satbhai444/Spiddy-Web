"""
FileDrop views — upload, download, preview, and success pages.
"""

import mimetypes
import os

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import File
from django.db.models import F
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..constants import (
    BLOCKED_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_UPLOAD_BYTES_PER_HOUR,
    MAX_UPLOADS_PER_HOUR,
)
from ..models import FileDrop
from ..utils import (
    check_pin_rate_limit,
    delete_expired,
    file_info_from_drop,
    fmt_size,
    get_client_ip,
    get_preview_type,
    record_failed_pin,
)


def upload_view(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        if not request.FILES.get('file'):
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'No file selected.'})
            return render(request, 'drop/upload.html')

        ip = get_client_ip(request)
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
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': msg})
            return render(request, 'drop/upload.html', {'error': msg})

        if chunk_index == 0 and upload_bytes >= MAX_UPLOAD_BYTES_PER_HOUR:
            msg = 'Hourly data limit reached. Max 5 GB per hour.'
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': msg})
            return render(request, 'drop/upload.html', {'error': msg})

        uploaded_file = request.FILES['file']
        filename = request.POST.get('filename', uploaded_file.name)

        # Check extensions early
        ext = os.path.splitext(filename)[1].lower()
        if ext in BLOCKED_EXTENSIONS:
            msg = f'File type "{ext}" is not allowed for security reasons.'
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': msg})
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
            one_time = request.POST.get('one_time') in ('true', 'on')
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


def success_view(request, pin):
    drop = get_object_or_404(FileDrop, pin=pin)
    if drop.is_expired():
        delete_expired(drop)
        return redirect('upload')
    return render(request, 'drop/success.html', {
        'pin': drop.pin,
        'filename': drop.original_filename or os.path.basename(drop.file.name),
        'share_url': request.build_absolute_uri(f'/get/{drop.pin}/'),
        'expires_hours': drop.expires_hours,
        'one_time': drop.one_time,
    })


def get_file_view(request, pin):
    """Direct share link — shows file info without requiring PIN entry."""
    ip = get_client_ip(request)
    locked, msg = check_pin_rate_limit(ip)
    if locked:
        return render(request, 'drop/download.html', {'error': msg})
    try:
        drop = FileDrop.objects.get(pin=pin)
        if drop.is_expired():
            delete_expired(drop)
            return render(request, 'drop/download.html', {'error': 'This link has expired.'})
        if drop.one_time and drop.download_count >= 1:
            return render(request, 'drop/download.html', {
                'error': 'This file was a one-time download and has already been retrieved.'
            })
        return render(request, 'drop/download.html', {'file_info': file_info_from_drop(drop)})
    except FileDrop.DoesNotExist:
        record_failed_pin(ip)
        return render(request, 'drop/download.html', {'error': 'Invalid link. File does not exist.'})


def file_preview_view(request, pin):
    drop = get_object_or_404(FileDrop, pin=pin)
    if drop.is_expired():
        delete_expired(drop)
        return HttpResponse('Expired', status=410)
    filename = drop.original_filename or os.path.basename(drop.file.name)
    preview_type = get_preview_type(filename)
    if not preview_type:
        return HttpResponse('Preview not available', status=415)
    content_type, _ = mimetypes.guess_type(filename)
    response = FileResponse(drop.file.open('rb'), content_type=content_type or 'application/octet-stream')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def download_view(request):
    error = None
    file_info = None
    if request.method == 'POST':
        ip = get_client_ip(request)
        locked, msg = check_pin_rate_limit(ip)
        if locked:
            return render(request, 'drop/download.html', {'error': msg})
        pin = request.POST.get('pin', '').strip()
        pwd = request.POST.get('password', '').strip()
        try:
            drop = FileDrop.objects.get(pin=pin)
            if drop.is_expired():
                delete_expired(drop)
                error = 'This PIN has expired.'
            elif drop.one_time and drop.download_count >= 1:
                error = 'This file was a one-time download and has already been retrieved.'
            elif drop.password and not drop.verify_password(pwd):
                error = '🔒 Incorrect password for this drop.'
                file_info = file_info_from_drop(drop)
                file_info['password_required'] = True
            else:
                cache.delete(f'pin_attempts_{ip}')
                file_info = file_info_from_drop(drop)
        except FileDrop.DoesNotExist:
            error = record_failed_pin(ip)
    return render(request, 'drop/download.html', {'error': error, 'file_info': file_info})


def file_download_view(request, pin):
    """Serves the actual file bytes; called by JS fetch for progress tracking."""
    ip = get_client_ip(request)
    locked, _ = check_pin_rate_limit(ip)
    if locked:
        return HttpResponse('Too many requests', status=429)
    try:
        drop = FileDrop.objects.get(pin=pin)
        if drop.is_expired():
            delete_expired(drop)
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
            delete_expired(drop)
            return response
        FileDrop.objects.filter(pk=drop.pk).update(download_count=F('download_count') + 1)
        return FileResponse(drop.file.open('rb'), as_attachment=True, filename=filename)
    except FileDrop.DoesNotExist:
        record_failed_pin(ip)
        return HttpResponse('Not found', status=404)
