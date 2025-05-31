from django import forms
from .models import Post
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

# Registration Form
class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=get_user_model().ROLE_CHOICES)

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'role', 'password1', 'password2']

# Post Creation Form
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['platform', 'content', 'image', 'scheduled_time', 'status']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Post'))