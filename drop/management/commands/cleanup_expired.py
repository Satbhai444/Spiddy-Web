from django.core.management.base import BaseCommand
from drop.models import FileDrop


class Command(BaseCommand):
    help = 'Delete expired file drops and their files from disk.'

    def handle(self, *args, **options):
        deleted = 0
        for drop in FileDrop.objects.all():
            if not drop.is_expired():
                continue
            if drop.file:
                drop.file.delete(save=False)
            drop.delete()
            deleted += 1
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} expired drop(s).'))
