from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    mobile_number = forms.CharField(max_length=11)
    password1 = forms.CharField()
    password2 = forms.CharField()
    profile_picture = forms.ImageField(required=False)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1, p2 = cleaned_data.get('password1'), cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data

    def save(self):
        email = self.cleaned_data['email']
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password1'],
            is_active=False,
        )
        Profile.objects.create(
            user=user,
            mobile_number=self.cleaned_data['mobile_number'],
            profile_picture=self.cleaned_data.get('profile_picture'),
        )
        return user

class ProfileEditForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    mobile_number = forms.CharField(max_length=11)
    profile_picture = forms.ImageField(required=False)
    birthdate = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    facebook_profile = forms.URLField(required=False)
    country = forms.CharField(max_length=100, required=False)

    def save(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

        profile = user.profile
        profile.mobile_number = self.cleaned_data['mobile_number']
        if self.cleaned_data.get('profile_picture'):
            profile.profile_picture = self.cleaned_data['profile_picture']
        profile.birthdate = self.cleaned_data.get('birthdate')
        profile.facebook_profile = self.cleaned_data.get('facebook_profile')
        profile.country = self.cleaned_data.get('country')
        profile.save()
        return user