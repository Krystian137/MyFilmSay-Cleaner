from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User


class RegisterForm(UserCreationForm):
    """Formularz rejestracji użytkownika"""

    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'class': 'form-control'
        })
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email Address',
            'class': 'form-control'
        })
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        })
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm Password',
            'class': 'form-control'
        })
    )

    class Meta:
        model = User
        fields = ['name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email.lower()  # Zapisz email małymi literami

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.name = self.cleaned_data['name']
        if commit:
            user.save()
        return user


class CustomLoginForm(AuthenticationForm):
    """Formularz logowania"""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email Address',
            'class': 'form-control',
            'autofocus': True
        })
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        })
    )

    def clean_username(self):
        # Normalizuj email do małych liter
        return self.cleaned_data.get('username', '').lower()


class UserProfileForm(forms.ModelForm):
    """Formularz edycji profilu użytkownika"""

    class Meta:
        model = User
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email tylko do odczytu (można zmienić jeśli chcesz)
        self.fields['email'].disabled = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Sprawdź czy email nie jest zajęty przez innego użytkownika
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise ValidationError("This email is already in use.")
        return email.lower()