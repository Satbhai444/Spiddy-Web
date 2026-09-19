"""
Spider-Verse Room views — create/join rooms, messaging, reactions, typing.
"""

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render

from ..constants import ALLOWED_REACTION_EMOJIS
from ..models import Room, RoomMessage
from ..utils import normalize_reactions, safe_cache_key


def create_room_view(request):
    if request.method == 'POST':
        sender_name = request.POST.get('sender_name', '').strip()
        avatar = request.POST.get('avatar', 'classic').strip()
        if not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Name is required'})

        # Create a new Room
        room = Room.objects.create()

        # Save credentials in session
        request.session['room_code'] = room.code
        request.session['sender_name'] = sender_name
        request.session['avatar'] = avatar

        # Create a system message welcoming the user
        RoomMessage.objects.create(
            room=room,
            sender_name='System (K.A.R.E.N)',
            avatar='karen',
            text_content=f"{sender_name} has created the web room! Share the code {room.code} with your friends."
        )

        return JsonResponse({'status': 'success', 'room_code': room.code})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def join_room_view(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        sender_name = request.POST.get('sender_name', '').strip()
        avatar = request.POST.get('avatar', 'classic').strip()

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
        request.session['avatar'] = avatar

        RoomMessage.objects.create(
            room=room,
            sender_name='System (K.A.R.E.N)',
            avatar='karen',
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
    avatar = request.session.get('avatar', 'classic')

    # If not authenticated for this room, redirect to home
    if session_code != room_code or not sender_name:
        return redirect('home')

    return render(request, 'drop/room.html', {
        'room': room,
        'sender_name': sender_name,
        'avatar': avatar
    })


def api_send_message(request, room_code):
    if request.method == 'POST':
        session_code = request.session.get('room_code')
        sender_name = (
            request.headers.get('X-Sender-Name')
            or request.POST.get('sender_name')
            or request.session.get('sender_name')
        )
        avatar = request.POST.get('avatar') or request.session.get('avatar', 'classic')
        is_voice_note = request.POST.get('is_voice_note') in ['1', 'true', 'True', True]

        if (session_code and session_code != room_code) or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        try:
            room = Room.objects.get(code=room_code)
        except Room.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Room not found'}, status=404)

        text_content = request.POST.get('text_content', '').strip()
        uploaded_file = request.FILES.get('file')
        reply_to_id = request.POST.get('reply_to_id')

        if not text_content and not uploaded_file:
            return JsonResponse({'status': 'error', 'message': 'Cannot send empty message'})

        original_filename = None
        if uploaded_file:
            original_filename = uploaded_file.name

        reply_msg = None
        if reply_to_id:
            try:
                reply_msg = RoomMessage.objects.filter(id=int(reply_to_id), room=room).first()
            except (ValueError, TypeError):
                reply_msg = None

        RoomMessage.objects.create(
            room=room,
            sender_name=sender_name,
            avatar=avatar,
            text_content=text_content,
            file=uploaded_file,
            original_filename=original_filename,
            reply_to=reply_msg,
            is_voice_note=is_voice_note
        )

        # Clear typing cache for this user since they sent the message
        cache.delete(safe_cache_key('typing', room_code, sender_name))

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def api_get_messages(request, room_code):
    if request.method == 'GET':
        session_code = request.session.get('room_code')
        sender_name = (
            request.headers.get('X-Sender-Name')
            or request.GET.get('sender_name')
            or request.session.get('sender_name')
        )

        if (session_code and session_code != room_code) or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        last_id = request.GET.get('last_id', 0)
        try:
            last_id = int(last_id)
        except ValueError:
            last_id = 0

        messages = (
            RoomMessage.objects
            .filter(room__code=room_code, id__gt=last_id)
            .select_related('reply_to')
            .order_by('id')
        )

        data = []
        for msg in messages:
            file_url = msg.file.url if msg.file else None
            reply_data = None
            if msg.reply_to:
                reply_data = {
                    'id': msg.reply_to.id,
                    'sender_name': msg.reply_to.sender_name,
                    'text': (
                        (msg.reply_to.text_content[:80] + '...')
                        if msg.reply_to.text_content and len(msg.reply_to.text_content) > 80
                        else (msg.reply_to.text_content or '')
                    ),
                    'is_file': bool(msg.reply_to.file),
                    'filename': msg.reply_to.original_filename or '',
                    'is_voice_note': msg.reply_to.is_voice_note,
                    'is_me': msg.reply_to.sender_name == sender_name
                }
            data.append({
                'id': msg.id,
                'sender_name': msg.sender_name,
                'avatar': msg.avatar or 'classic',
                'text_content': msg.text_content,
                'file_url': file_url,
                'original_filename': msg.original_filename,
                'is_voice_note': msg.is_voice_note,
                'is_deleted': msg.is_deleted,
                'created_at': msg.created_at.strftime("%I:%M %p"),
                'is_me': msg.sender_name == sender_name,
                'is_system': msg.sender_name == 'System (K.A.R.E.N)',
                'reply_to': reply_data,
                'reactions': normalize_reactions(msg.reactions)
            })

        # Real-time sync: Return reactions & deleted state map for recent messages
        # so all participants update instantly
        recent_active = RoomMessage.objects.filter(room__code=room_code).order_by('-id')[:60]
        reactions_map = {
            m.id: {
                'reactions': normalize_reactions(m.reactions),
                'is_deleted': m.is_deleted,
                'text_content': m.text_content if m.is_deleted else None
            }
            for m in recent_active
        }

        # Get active typers
        typers_list = cache.get(f'room_typers_{room_code}') or []
        active_typers = [
            t for t in typers_list
            if t != sender_name and cache.get(safe_cache_key('typing', room_code, t))
        ]

        return JsonResponse({
            'status': 'success',
            'messages': data,
            'reactions_map': reactions_map,
            'active_typers': active_typers
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def api_toggle_reaction(request, room_code, message_id):
    if request.method == 'POST':
        session_code = request.session.get('room_code')
        sender_name = (
            request.headers.get('X-Sender-Name')
            or request.POST.get('sender_name')
            or request.session.get('sender_name')
        )
        avatar = request.POST.get('avatar') or request.session.get('avatar', 'classic')

        if (session_code and session_code != room_code) or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        try:
            msg = RoomMessage.objects.get(id=message_id, room__code=room_code)
        except RoomMessage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)

        if msg.is_deleted:
            return JsonResponse({'status': 'error', 'message': 'Cannot react to deleted message'}, status=400)

        emoji = request.POST.get('emoji', '').strip()
        if emoji not in ALLOWED_REACTION_EMOJIS:
            return JsonResponse({'status': 'error', 'message': 'Invalid emoji'}, status=400)

        reactions = dict(msg.reactions or {})
        user_list = list(reactions.get(emoji, []))

        # Check if already reacted
        existing_idx = -1
        for idx, u in enumerate(user_list):
            u_name = u['name'] if isinstance(u, dict) else str(u)
            if u_name.strip().lower() == sender_name.strip().lower():
                existing_idx = idx
                break

        if existing_idx >= 0:
            user_list.pop(existing_idx)
            if not user_list:
                reactions.pop(emoji, None)
            else:
                reactions[emoji] = user_list
        else:
            user_list.append({'name': sender_name, 'avatar': avatar})
            reactions[emoji] = user_list

        msg.reactions = reactions
        msg.save(update_fields=['reactions'])

        return JsonResponse({'status': 'success', 'reactions': normalize_reactions(reactions)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)


def api_delete_message(request, room_code, message_id):
    if request.method == 'POST':
        session_code = request.session.get('room_code')
        sender_name = (
            request.headers.get('X-Sender-Name')
            or request.POST.get('sender_name')
            or request.session.get('sender_name')
        )

        if (session_code and session_code != room_code) or not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        try:
            msg = RoomMessage.objects.get(id=message_id, room__code=room_code)
        except RoomMessage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)

        if msg.sender_name.strip().lower() != sender_name.strip().lower():
            return JsonResponse({'status': 'error', 'message': 'Permission denied: only author can delete'}, status=403)

        msg.is_deleted = True
        msg.text_content = 'This message was deleted'
        msg.file = None
        msg.original_filename = None
        msg.reactions = {}
        msg.save(update_fields=['is_deleted', 'text_content', 'file', 'original_filename', 'reactions'])

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)


def api_typing_indicator(request, room_code):
    if request.method == 'POST':
        sender_name = (
            request.headers.get('X-Sender-Name')
            or request.POST.get('sender_name')
            or request.session.get('sender_name')
        )
        if not sender_name:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

        cache.set(safe_cache_key('typing', room_code, sender_name), sender_name, timeout=4)
        typers = set(cache.get(f'room_typers_{room_code}') or [])
        typers.add(sender_name)
        cache.set(f'room_typers_{room_code}', list(typers), timeout=15)

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=405)
