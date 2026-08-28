from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Post, Comment

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")
        return cleaned_data

class UserProfileForm(forms.ModelForm):
    display_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control text-white', 'style': 'background: #262626; border: 1px solid #363636;', 'placeholder': 'Name'}),
        required=False,
        label="Name"
    )
    gender = forms.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select text-white', 'style': 'background: #262626; border: 1px solid #363636;'}),
        required=False,
        label="Pronouns / Gender"
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control text-white', 'rows': 3, 'style': 'background: #262626; border: 1px solid #363636;', 'placeholder': 'Bio...'}),
        required=False
    )
    profile_pic = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'form-control text-white', 'style': 'background: #262626; border: 1px solid #363636;'}),
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['display_name', 'gender', 'bio', 'profile_pic']

    def clean_profile_pic(self):
        pic = self.cleaned_data.get('profile_pic')
        if pic and hasattr(pic, 'file'):
            from .utils.media import compress_and_optimize_image
            return compress_and_optimize_image(pic, max_dimension=800, quality=85)
        return pic

class PostForm(forms.ModelForm):
    caption = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What\'s on your mind?'}), required=False)
    image = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control'}), required=False)
    video = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}), required=False)

    class Meta:
        model = Post
        fields = ['caption', 'image', 'video']

    def clean_image(self):
        img = self.cleaned_data.get('image')
        if img and hasattr(img, 'file'):
            from .utils.media import compress_and_optimize_image
            return compress_and_optimize_image(img, max_dimension=1600, quality=85)
        return img

    def clean(self):
        cleaned_data = super().clean()
        caption = cleaned_data.get('caption')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')

        if not caption and not image and not video:
            raise forms.ValidationError("You must provide either a caption, image, or video.")
        return cleaned_data

class CommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Write a comment...'}), label="")

    class Meta:
        model = Comment
        fields = ['content']
