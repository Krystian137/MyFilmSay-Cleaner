from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Movie, Comment


class CreateMovieForm(forms.ModelForm):
    """Formularz tworzenia/edycji filmu"""

    class Meta:
        model = Movie
        fields = [
            'title', 'date', 'body', 'img_url', 'rating',
            'director', 'writers', 'genres'
        ]
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter movie description...'
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'Movie title'
            }),
            'date': forms.TextInput(attrs={
                'placeholder': 'YYYY'
            }),
            'img_url': forms.URLInput(attrs={
                'placeholder': 'https://example.com/image.jpg'
            }),
            'rating': forms.NumberInput(attrs={
                'step': '0.1',
                'min': '0',
                'max': '10'
            }),
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
    """Formularz dodawania komentarza"""

    parent_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        model = Comment
        fields = ['text', 'user_rating']
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Write your comment...',
                'class': 'form-control'
            }),
            'user_rating': forms.NumberInput(attrs={
                'step': '0.5',
                'min': '0',
                'max': '10',
                'placeholder': 'Rate this movie (0-10)',
                'class': 'form-control'
            }),
        }
        labels = {
            'text': 'Your Comment',
            'user_rating': 'Your Rating',
        }

    def __init__(self, *args, is_reply=False, **kwargs):
        super().__init__(*args, **kwargs)

        # Jeśli to odpowiedź, usuń pole ratingu
        if is_reply:
            self.fields.pop('user_rating', None)
            self.fields['text'].widget.attrs['placeholder'] = 'Write your reply...'

    def clean(self):
        cleaned_data = super().clean()
        parent_id = cleaned_data.get('parent_id')
        user_rating = cleaned_data.get('user_rating')

        # Jeśli to nie jest odpowiedź (parent_id is None), rating jest wymagany
        if not parent_id and not user_rating:
            raise forms.ValidationError(
                "Rating is required for main comments."
            )

        return cleaned_data


class FindMovieForm(forms.Form):
    """Formularz wyszukiwania filmu w TMDB API"""

    title = forms.CharField(
        label="Movie Title",
        max_length=250,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search for a movie...',
            'class': 'form-control'
        })
    )


class MovieSearchForm(forms.Form):
    """Formularz wyszukiwania filmów w bazie"""

    query = forms.CharField(
        label="Search",
        max_length=250,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search movies, directors, genres...',
            'class': 'form-control'
        })
    )