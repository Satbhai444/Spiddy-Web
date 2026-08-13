import random
import string
from datetime import timedelta
from django.db import models
from django.utils import timezone

def generate_pin():
    return ''.join(random.choices(string.digits, k=6))

from django.contrib.auth.hashers import make_password, check_password

class FileDrop(models.Model):
    EXPIRY_CHOICES = [(1, '1 Hour'), (6, '6 Hours'), (24, '24 Hours'), (168, '7 Days')]

    file = models.FileField(upload_to='drops/')
    original_filename = models.CharField(max_length=255, default='')
    pin = models.CharField(max_length=6, default=generate_pin, unique=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_hours = models.IntegerField(default=24, choices=EXPIRY_CHOICES)
    one_time = models.BooleanField(default=False)
    download_count = models.IntegerField(default=0)

    def set_password(self, raw_password):
        if raw_password:
            self.password = make_password(raw_password)
        else:
            self.password = None

    def verify_password(self, raw_password):
        if not self.password:
            return True
        return check_password(raw_password or '', self.password)

    def get_expiry(self):
        return self.created_at + timedelta(hours=self.expires_hours)

    def is_expired(self):
        return timezone.now() > self.get_expiry()

    def __str__(self):
        return f"{self.pin} - {self.original_filename or self.file.name}"
