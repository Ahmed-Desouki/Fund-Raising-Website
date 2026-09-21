from django.shortcuts import render

def register_view(request):
    # Path relative to the 'templates' directory:
    return render(request, 'registration/register.html')