"""
SpiddyWeb — Shared utility functions.

Helper functions used across multiple view modules. Extracted from the
monolithic views.py so they can be imported independently without circular
dependencies.
"""

import hashlib
import os

from django.core.cache import cache
from django.utils import timezone

from .constants import (
    MAX_PIN_ATTEMPTS,
    PIN_LOCKOUT_SECONDS,
    PREVIEW_AUDIO_EXTS,
    PREVIEW_IMAGE_EXTS,
    PREVIEW_TEXT_EXTS,
    PREVIEW_VIDEO_EXTS,
)


# ── Formatting ────────────────────────────────────────────────────────────────

def fmt_size(b):
    """Human-readable file size string."""
    if b < 1024:
        return f"{b} B"
    if b < 1048576:
        return f"{b / 1024:.1f} KB"
    return f"{b / 1048576:.2f} MB"


# ── File Helpers ──────────────────────────────────────────────────────────────

def get_preview_type(filename):
    """Return the preview category for a file, or ``None`` if unsupported."""
    ext = os.path.splitext(filename.lower())[1]
    if ext in PREVIEW_IMAGE_EXTS:
        return 'image'
    if ext in PREVIEW_VIDEO_EXTS:
        return 'video'
    if ext in PREVIEW_AUDIO_EXTS:
        return 'audio'
    if ext == '.pdf':
        return 'pdf'
    if ext in PREVIEW_TEXT_EXTS:
        return 'text'
    return None


def delete_expired(drop):
    """Remove a drop's backing file from disk and delete the DB row."""
    if drop.file and os.path.exists(drop.file.path):
        os.remove(drop.file.path)
    drop.delete()


# ── Request Helpers ───────────────────────────────────────────────────────────

def get_client_ip(request):
    """Extract the real client IP, respecting ``X-Forwarded-For``."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


# ── PIN Rate-Limiting ─────────────────────────────────────────────────────────

def check_pin_rate_limit(ip):
    """Return ``(is_locked, message)`` for the given IP."""
    if cache.get(f'pin_lockout_{ip}'):
        return True, '🔒 Too many failed attempts. Try again in 15 minutes.'
    return False, None


def record_failed_pin(ip):
    """Increment failed-PIN counter for *ip*; return a user-facing message."""
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


# ── FileDrop Info ─────────────────────────────────────────────────────────────

def file_info_from_drop(drop):
    """Build a template-ready dict describing a :class:`FileDrop`."""
    remaining_ms = int((drop.get_expiry() - timezone.now()).total_seconds() * 1000)
    name = drop.original_filename or os.path.basename(drop.file.name)
    preview_type = get_preview_type(name)
    return {
        'pin': drop.pin,
        'name': name,
        'size': fmt_size(drop.file.size),
        'expires_ms': remaining_ms,
        'one_time': drop.one_time,
        'has_password': bool(drop.password),
        'download_count': drop.download_count,
        'previewable': bool(preview_type),
        'preview_type': preview_type,
    }


# ── Room Helpers ──────────────────────────────────────────────────────────────

def safe_cache_key(prefix, room_code, name):
    """Build a cache key safe for any sender name (hashed)."""
    h = hashlib.md5((name or '').encode('utf-8')).hexdigest()[:12]
    return f'{prefix}_{room_code}_{h}'


def normalize_reactions(reactions):
    """Ensure every reaction user entry is a ``{name, avatar}`` dict."""
    normalized = {}
    for emoji, users in (reactions or {}).items():
        norm_list = []
        for u in users:
            if isinstance(u, dict):
                norm_list.append(u)
            else:
                norm_list.append({'name': str(u), 'avatar': 'classic'})
        if norm_list:
            normalized[emoji] = norm_list
    return normalized
