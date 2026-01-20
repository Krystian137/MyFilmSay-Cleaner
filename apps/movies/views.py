from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db.models import Q, Prefetch
from django.views import View
import requests
import json
import random
import os
from dotenv import load_dotenv

from .models import Movie, Comment, Vote
from .forms import CreateMovieForm, CommentForm, FindMovieForm
from apps.users.models import User

load_dotenv()

API_KEY = os.getenv("API_KEY_TMDb")
API_URL = "https://api.themoviedb.org/3/search/movie"
API_IMG_URL = "https://image.tmdb.org/t/p/w500"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"


# Mixins dla uprawnień
class AdminRequiredMixin(UserPassesTestMixin):
    """Wymaga uprawnień admina"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('movies:list')


class ModeratorRequiredMixin(UserPassesTestMixin):
    """Wymaga uprawnień moderatora lub admina"""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_moderator

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('movies:list')


# ==================== WIDOKI FILMÓW ====================

class MovieListView(ListView):
    """Lista wszystkich filmów z sortowaniem i losowymi rekomendacjami"""
    model = Movie
    template_name = 'movies/index.html'
    context_object_name = 'all_movies'
    paginate_by = 20

    def get_queryset(self):
        sort_by = self.request.GET.get('sort_by', 'title')

        if sort_by == 'rating':
            return Movie.objects.order_by('-rating')
        elif sort_by == 'date':
            return Movie.objects.order_by('-date')
        else:
            return Movie.objects.order_by('title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_movies = list(self.get_queryset())
        context['random_movies'] = random.sample(all_movies, min(3, len(all_movies)))
        context['current_sort'] = self.request.GET.get('sort_by', 'title')
        return context


class MovieDetailView(DetailView):
    """Szczegóły filmu z komentarzami"""
    model = Movie
    template_name = 'movies/movie.html'
    context_object_name = 'movie'
    pk_url_kwarg = 'movie_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offset = int(self.request.GET.get("offset", 0))

        # Komentarze z prefetch replies
        comments = Comment.objects.filter(
            movie=self.object,
            parent__isnull=True  # Tylko główne komentarze
        ).prefetch_related(
            'author',
            Prefetch('replies', queryset=Comment.objects.select_related('author').order_by('timestamp'))
        ).order_by('-timestamp')[offset:offset + 5]

        context.update({
            'form': CommentForm(),
            'comments': comments,
            'total_comments': Comment.objects.filter(movie=self.object, parent__isnull=True).count(),
            'current_user_id': self.request.user.id if self.request.user.is_authenticated else None,
            'rating_percentage': self.object.rating * 10 if self.object.rating else 0,
            'offset': offset,
            'star_range': range(1, 11),
        })
        return context


class MovieSearchView(ListView):
    """Wyszukiwarka filmów"""
    model = Movie
    template_name = 'movies/search_results.html'
    context_object_name = 'search_results'

    def get_queryset(self):
        query = self.request.GET.get('query', '')
        if query:
            return Movie.objects.filter(
                Q(title__icontains=query) |
                Q(director__icontains=query) |
                Q(genres__icontains=query)
            )
        return Movie.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('query', '')
        return context


class MovieCreateView(ModeratorRequiredMixin, CreateView):
    """Ręczne dodawanie filmu (dla adminów/moderatorów)"""
    model = Movie
    form_class = CreateMovieForm
    template_name = 'movies/add_movie.html'
    success_url = reverse_lazy('movies:list')

    def form_valid(self, form):
        messages.success(self.request, "Movie added successfully!")
        return super().form_valid(form)


class MovieUpdateView(ModeratorRequiredMixin, UpdateView):
    """Edycja filmu"""
    model = Movie
    form_class = CreateMovieForm
    template_name = 'movies/edit_movie.html'
    pk_url_kwarg = 'movie_id'

    def get_success_url(self):
        messages.success(self.request, "Movie updated successfully!")
        return reverse('movies:detail', kwargs={'movie_id': self.object.id})


class MovieDeleteView(ModeratorRequiredMixin, DeleteView):
    """Usuwanie filmu"""
    model = Movie
    pk_url_kwarg = 'movie_id'
    success_url = reverse_lazy('movies:list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Movie deleted successfully!")
        return super().delete(request, *args, **kwargs)


# ==================== TMDB API VIEWS ====================

class FindMovieView(ModeratorRequiredMixin, View):
    """Wyszukiwanie filmu w TMDB API"""
    template_name = 'movies/find_movie.html'

    def get(self, request):
        form = FindMovieForm()
        return self.render(request, form)

    def post(self, request):
        form = FindMovieForm(request.POST)
        if form.is_valid():
            movie_title = form.cleaned_data["title"]
            response = requests.get(API_URL, params={"api_key": API_KEY, "query": movie_title})
            data = response.json().get("results", [])
            return self.render(request, form, data)
        return self.render(request, form)

    def render(self, request, form, results=None):
        context = {'form': form}
        if results:
            context['options'] = results
        return render(request, self.template_name, context)


class ImportMovieFromTMDBView(ModeratorRequiredMixin, View):
    """Import filmu z TMDB do bazy danych"""

    def get(self, request, movie_id):
        try:
            # Pobierz dane filmu
            response = requests.get(f"{MOVIE_DB_INFO_URL}/{movie_id}", params={"api_key": API_KEY})
            data = response.json()

            # Pobierz credits (reżyser, scenarzyści)
            credits_response = requests.get(
                f"{MOVIE_DB_INFO_URL}/{movie_id}/credits",
                params={"api_key": API_KEY}
            )
            credits_data = credits_response.json()

            # Przetwórz dane
            director = ", ".join([
                crew["name"] for crew in credits_data.get("crew", [])
                if crew["job"] == "Director"
            ])
            writers = ", ".join([
                crew["name"] for crew in credits_data.get("crew", [])
                if crew["job"] in ["Writer", "Screenplay"]
            ])
            genres = ", ".join([g["name"] for g in data.get("genres", [])])
            img_url = f"{API_IMG_URL}{data['poster_path']}" if data.get("poster_path") else None

            # Utwórz film
            new_movie = Movie.objects.create(
                title=data["title"],
                date=data["release_date"].split("-")[0] if data.get("release_date") else "",
                img_url=img_url,
                body=data.get("overview", ""),
                rating=data.get("vote_average"),
                director=director,
                writers=writers,
                genres=genres
            )

            messages.success(request, f"Movie '{new_movie.title}' imported successfully!")
            return redirect("movies:update", movie_id=new_movie.id)

        except Exception as e:
            messages.error(request, f"Error importing movie: {str(e)}")
            return redirect("movies:find")


# ==================== KOMENTARZE ====================

class CommentCreateView(LoginRequiredMixin, View):
    """Dodawanie komentarza lub odpowiedzi"""

    def post(self, request, movie_id):
        movie = get_object_or_404(Movie, id=movie_id)
        form = CommentForm(request.POST)

        if form.is_valid():
            parent_id = form.cleaned_data.get('parent_id')
            parent = get_object_or_404(Comment, id=parent_id) if parent_id else None

            Comment.objects.create(
                text=form.cleaned_data['text'],
                author=request.user,
                movie=movie,
                user_rating=form.cleaned_data.get('user_rating'),
                parent=parent
            )

            messages.success(request, "Comment added successfully!")
            return redirect('movies:detail', movie_id=movie_id)

        messages.error(request, "Invalid comment data.")
        return redirect('movies:detail', movie_id=movie_id)


class CommentDeleteView(LoginRequiredMixin, View):
    """Usuwanie komentarza"""

    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)

        # Sprawdź uprawnienia
        if not (request.user.id == comment.author.id or
                request.user.is_admin or
                request.user.is_moderator):
            return JsonResponse({
                "success": False,
                "message": "You don't have permission to delete this comment."
            })

        # Usuń powiązane głosy
        Vote.objects.filter(comment=comment).delete()

        # Usuń komentarz (kaskadowo usuwa odpowiedzi)
        comment.delete()

        return JsonResponse({"success": True})


# ==================== GŁOSOWANIE ====================

class VoteView(LoginRequiredMixin, View):
    """Głosowanie na komentarze (like/dislike)"""

    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8'))
            comment_id = data.get('comment_id')
            vote_type = data.get('vote_type')

            if not comment_id or vote_type not in ['like', 'dislike']:
                return JsonResponse({
                    "success": False,
                    "message": "Invalid data"
                }, status=400)

            # Usuń prefix jeśli istnieje
            actual_id = comment_id.replace("comment-", "")
            comment = get_object_or_404(Comment, id=actual_id)

            # Sprawdź istniejący głos
            existing_vote = Vote.objects.filter(
                user=request.user,
                comment=comment
            ).first()

            if existing_vote:
                if existing_vote.vote_type == vote_type:
                    # Usuń głos (toggle off)
                    existing_vote.delete()
                    if vote_type == 'like':
                        comment.likes_count = max(0, comment.likes_count - 1)
                    else:
                        comment.dislikes_count = max(0, comment.dislikes_count - 1)
                else:
                    # Zmień głos
                    if existing_vote.vote_type == 'like':
                        comment.likes_count = max(0, comment.likes_count - 1)
                        comment.dislikes_count += 1
                    else:
                        comment.dislikes_count = max(0, comment.dislikes_count - 1)
                        comment.likes_count += 1

                    existing_vote.vote_type = vote_type
                    existing_vote.save()
            else:
                # Nowy głos
                Vote.objects.create(
                    user=request.user,
                    comment=comment,
                    vote_type=vote_type
                )
                if vote_type == 'like':
                    comment.likes_count += 1
                else:
                    comment.dislikes_count += 1

            comment.save()

            return JsonResponse({
                "success": True,
                "likes": comment.likes_count,
                "dislikes": comment.dislikes_count
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            }, status=500)


# ==================== AJAX ====================

class LoadCommentsView(View):
    """AJAX loading więcej komentarzy"""

    def get(self, request, movie_id):
        offset = int(request.GET.get("offset", 0))
        comments = Comment.objects.filter(
            movie_id=movie_id,
            parent__isnull=True
        ).select_related('author').prefetch_related(
            Prefetch('replies', queryset=Comment.objects.select_related('author'))
        ).order_by("-timestamp")[offset:offset + 5]

        html = render(request, "movies/partials/comment_list.html", {
            "comments": comments,
            "user": request.user,
            "star_range": range(1, 11),
        }).content.decode("utf-8")

        return JsonResponse({"html": html})