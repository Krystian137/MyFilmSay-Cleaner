from django import forms
from .models import Movie, Comment


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = [
            'title', 'date', 'body', 'img_url', 'rating', 'director', 'writers', 'genres'
        ]
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5,'placeholder': 'Enter movie description'}),
            'title': forms.TextInput(attrs={'placeholder': 'Movie title'}),
            'date': forms.TextInput(attrs={'placeholder': 'YYYY'}),
            'img_url': forms.URLInput(attrs={'placeholder': 'https://example.com/image.jpg'}),
            'rating': forms.NumberInput(attrs={'step': '0.1','min': '0', 'max': '10','placeholder': 'Rating (0-10)'}),
        }
        labels = {
            'body': 'Description',
            'img_url': 'Poster URL',
            'date': 'Release Year',
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 0 or rating > 10):
            raise forms.ValidationError("Rating must be between 0 and 10.")
        return rating


class CommentForm(forms.ModelForm):
    parent_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False
    )
    class Meta:
        model = Comment
        fields = ['text', 'user_rating']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your comment', 'class': 'form-control'}),
            'user_rating': forms.NumberInput(attrs={'step': '0.5', 'min': '0', 'max': '10','placeholder': 'Rate this movie (0-10)',
                                                    'class': 'form-control'}),
        }
        labels = {
            'text': 'Your Comment',
            'user_rating': 'Your Rating',
        }


class FindMovieForm(forms.Form):
    title = forms.CharField(
        label="Movie Title",
        max_length=250,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search for a movie...',
            'class': 'form-control'
        })
    )