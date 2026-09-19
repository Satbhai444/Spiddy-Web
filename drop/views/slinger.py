import random
from django.shortcuts import render

def slinger_view(request):
    # Pass a randomly generated 6-digit PIN to the template as a room identifier
    # (The user doesn't have to use this if they are joining, but it helps if they are hosting)
    random_pin = f"{random.randint(0, 999999):06d}"
    return render(request, 'drop/slinger.html', {'random_pin': random_pin})
