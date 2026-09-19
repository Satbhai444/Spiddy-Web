from django import forms
from django.core.exceptions import ValidationError

from .constants import BLOCKED_EXTENSIONS, MAX_FILE_SIZE


class ContactForm(forms.Form):
    """Form for the SpideyHQ contact page."""
    subject = forms.ChoiceField(
        choices=[
            ('General', 'General'),
            ('Support', 'Support'),
            ('DMCA', 'DMCA / Abuse'),
            ('Business', 'Business'),
        ],
        required=True
    )
    email = forms.EmailField(required=False)
    message = forms.CharField(widget=forms.Textarea, required=True, min_length=10)


class FileUploadForm(forms.Form):
    """Validation logic for file uploads."""
    file = forms.FileField(required=True)
    expires_hours = forms.ChoiceField(
        choices=[
            ('1', '1 Hour'),
            ('6', '6 Hours'),
            ('24', '24 Hours'),
            ('168', '7 Days')
        ],
        required=False,
        initial='24'
    )
    password = forms.CharField(required=False)
    one_time = forms.BooleanField(required=False)

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if uploaded_file:
            if uploaded_file.size > MAX_FILE_SIZE:
                raise ValidationError("File exceeds 2GB limit.")
            
            ext = '.' + uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
            if ext in BLOCKED_EXTENSIONS:
                raise ValidationError(f'File type "{ext}" is not allowed for security reasons.')
                
        return uploaded_file
