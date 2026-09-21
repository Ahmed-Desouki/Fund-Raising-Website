from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .forms import RegisterForm
from .tokens import account_activation_token

def auth_page(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')
    return render(request, 'registration/register.html')


@require_POST
def api_register(request):
    form = RegisterForm(request.POST, request.FILES)
    if form.is_valid():
        user = form.save()
        send_activation_email(request, user)
        return JsonResponse({
            'success': True,
            'message': 'Account created. Check your email to activate your account before logging in.'
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@require_POST
def api_login(request):
    email = request.POST.get('email')
    password = request.POST.get('password')

    try:
        existing_user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        existing_user = None

    # Wrong password (or no such user) always gets the generic message —
    # only a *correct* password reveals the "please activate" state.
    if existing_user is None or not existing_user.check_password(password):
        return JsonResponse({'success': False, 'error': 'Invalid email or password.'}, status=401)

    if not existing_user.is_active:
        return JsonResponse({
            'success': False,
            'error': 'Please activate your account via the link sent to your email before logging in.'
        }, status=403)

    user = authenticate(request, username=email, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'success': True, 'redirect_url': '/dashboard/'})

    return JsonResponse({'success': False, 'error': 'Invalid email or password.'}, status=401)

@login_required
def logout_view(request):
    logout(request)
    return redirect('auth_page')


@login_required
def dashboard_view(request):
    return render(request, 'main/dashboard.html')

def send_activation_email(request, user):
    current_site = get_current_site(request)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    activation_link = f"http://{current_site.domain}/activate/{uid}/{token}/"

    subject = "Activate your account"
    message = (
        f"Hi {user.first_name},\n\n"
        f"Thanks for signing up. Click the link below to activate your account. "
        f"This link expires in 24 hours.\n\n{activation_link}\n\n"
        f"If you didn't create this account, you can ignore this email."
    )
    send_mail(subject, message, None, [user.email])

def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user, backend='main.backends.EmailBackend')
        return redirect('dashboard')

    return render(request, 'registration/activation_invalid.html')

from .forms import RegisterForm, ProfileEditForm


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(request.user)
            return redirect('profile')
        # fall through and re-render with errors
    else:
        profile = request.user.profile
        form = ProfileEditForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'mobile_number': profile.mobile_number,
            'birthdate': profile.birthdate,
            'facebook_profile': profile.facebook_profile,
            'country': profile.country,
        })

    return render(request, 'main/profile.html', {'form': form})


@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()  # CASCADE also removes the linked Profile row
    return redirect('auth_page')