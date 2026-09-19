"""
Static page views — home, privacy, terms, DMCA, contact, docs, HQ, 404.
"""

import os

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Count
from django.shortcuts import redirect, render

from ..constants import MAX_CONTACT_PER_HOUR
from ..models import FileDrop
from ..utils import delete_expired, fmt_size, get_client_ip


def home_view(request):
    drops = list(FileDrop.objects.all())
    stats = FileDrop.objects.aggregate(total_files=Count('id'))
    active_count = sum(1 for drop in drops if not drop.is_expired())
    total_bytes = sum(drop.file.size for drop in drops if drop.file)
    return render(request, 'drop/home.html', {
        'stats': {
            'active_files': active_count,
            'total_files': stats['total_files'] or 0,
            'total_shared': fmt_size(total_bytes),
        }
    })


def privacy_view(request):
    return render(request, 'drop/privacy.html')


def terms_view(request):
    return render(request, 'drop/terms.html')


def dmca_view(request):
    return render(request, 'drop/dmca.html')


def contact_view(request):
    sent = False
    error = None
    if request.method == 'POST':
        ip = get_client_ip(request)
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


def hq_view(request):
    """Spidey HQ Admin Dashboard"""
    drops = list(FileDrop.objects.all())
    active_drops = [d for d in drops if not d.is_expired()]
    expired_drops = [d for d in drops if d.is_expired()]

    # Action: Manual Purge
    purged_count = 0
    if request.method == 'POST' and request.POST.get('action') == 'purge':
        for exp in expired_drops:
            delete_expired(exp)
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
        'total_storage_fmt': fmt_size(total_bytes),
        'active_storage_fmt': fmt_size(active_bytes),
        'active_drops': active_drops[:20],  # top 20
        'ext_counts': ext_counts,
        'purged_count': purged_count,
    })


def docs_view(request):
    """SpiddyWeb Interactive Documentation & API Guide"""
    return render(request, 'drop/docs.html')


def custom_404_view(request, exception=None):
    """Spidey Custom 404 Multiverse Error Page"""
    return render(request, 'drop/404.html', status=404)
