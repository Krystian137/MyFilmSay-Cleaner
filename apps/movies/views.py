import re
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
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
from .forms import MovieForm, CommentForm, FindMovieForm

load_dotenv()

API_KEY = os.getenv("API_KEY_TMDb")
API_URL = "https://api.themoviedb.org/3/search/movie"
API_IMG_URL = "https://image.tmdb.org/t/p/w500"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"

# Check if user has permissions
class PermissionMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin or self.request.user.is_moderator

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('movies:list')

# List of movies with a sorting option
class MovieListView(ListView):
    model = Movie
    template_name = 'movies/movie_list.html'
    context_object_name = 'all_movies'
    # Sorting
    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get('search')
        # Sort by title, rating, date
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(rating__icontains=search_query) |
                Q(date__icontains=search_query)
            )

        sort = self.request.GET.get('sort', 'title')
        order = self.request.GET.get('order', 'asc')
        allowed_sorts = {'title', 'rating', 'date'}

        if sort in allowed_sorts:
            if order == 'desc':
                sort = f'-{sort}'
            queryset = queryset.order_by(sort)

        queryset = queryset.select_related()
        return queryset

    # Carousel with random movies
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_movies = list(self.get_queryset())
        context['random_movies'] = random.sample(all_movies, min(3, len(all_movies)))
        context['current_sort'] = self.request.GET.get('sort_by', 'title')
        return context

# Movie subpage view with a comment section
class MovieDetailView(DetailView):
    model = Movie
    template_name = 'movies/movie_detail.html'
    context_object_name = 'movie'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    # Get comments and other context data
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        comments = Comment.objects.filter(
            movie=self.object,
            parent__isnull=True
        ).prefetch_related(
            'author',
            Prefetch('replies', queryset=Comment.objects.select_related('author').order_by('timestamp'))
        )

        context.update({
            'form': CommentForm(),
            'comments': comments,
            'total_comments': Comment.objects.filter(movie=self.object, parent__isnull=True).count(),
            'current_user_id': self.request.user.id if self.request.user.is_authenticated else None,
            'rating_percentage': self.object.rating * 10 if self.object.rating else 0,
            'star_range': range(1, 11),
        })
        return context

# Movie search view, search by title, director, genre
class MovieSearchView(ListView):
    model = Movie
    template_name = 'movies/movie_search.html'
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

# Create, Update, Delete views for movies with permission checks
class MovieCreateView(PermissionMixin, CreateView):
    model = Movie
    form_class = MovieForm
    template_name = 'movies/movie_form.html'
    success_url = reverse_lazy('movies:list')

    def form_valid(self, form):
        messages.success(self.request, "Movie added successfully!")
        return super().form_valid(form)


class MovieUpdateView(PermissionMixin, UpdateView):
    model = Movie
    form_class = MovieForm
    template_name = 'movies/movie_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        messages.success(self.request, "Movie updated successfully!")
        return reverse('movies:detail', kwargs={'slug': self.object.slug})


class MovieDeleteView(PermissionMixin, DeleteView):
    model = Movie
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('movies:list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Movie deleted successfully!")
        return super().delete(request, *args, **kwargs)

# Find and import movies from TMDb
class FindMovieView(PermissionMixin, View):
    template_name = 'movies/tmdb_search.html'
    def get(self, request):
        form = FindMovieForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = FindMovieForm(request.POST)
        if form.is_valid():
            movie_title = form.cleaned_data["title"]
            response = requests.get(API_URL, params={"api_key": API_KEY, "query": movie_title})
            data = response.json().get("results", [])
            return render(request, self.template_name, {'form': form, 'options': data})
        return render(request, self.template_name, {'form': form})

# Import selected movie from TMDb into local database
class ImportMovieFromTMDBView(PermissionMixin, View):
    def get(self, request, movie_id):
        try:
            response = requests.get(f"{MOVIE_DB_INFO_URL}/{movie_id}", params={"api_key": API_KEY})
            data = response.json()
            # Fetch credits to get director and writers
            credits_response = requests.get(
                f"{MOVIE_DB_INFO_URL}/{movie_id}/credits",
                params={"api_key": API_KEY}
            )
            credits_data = credits_response.json()

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
            # Create and save the new movie
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
            return redirect("movies:update", slug=new_movie.slug)

        except Exception as e:
            messages.error(request, f"Error importing movie: {str(e)}")
            return redirect("movies:find")

# Comment views: create, edit, delete, vote, normal View classes for JSON responses
class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, movie_id):
        movie = get_object_or_404(Movie, id=movie_id)

        text = request.POST.get('text')
        user_rating = request.POST.get('user_rating')
        parent_id = request.POST.get('parent_id')

        if not text:
            messages.error(request, "Comment text is required.")
            return redirect('movies:detail', slug=movie.slug)

        if not parent_id and not user_rating:
            messages.error(request, "Rating is required for main comments.")
            return redirect('movies:detail', slug=movie.slug)

        parent = get_object_or_404(Comment, id=parent_id) if parent_id else None

        Comment.objects.create(
            text=text,
            author=request.user,
            movie=movie,
            user_rating=float(user_rating) if user_rating else None,
            parent=parent
        )

        messages.success(request, "Comment added successfully!")
        return redirect('movies:detail', slug=movie.slug)


class CommentEditView(LoginRequiredMixin, View):
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)

        if request.user.id != comment.author.id:
            return JsonResponse({"success": False, "message": "Permission denied"}, status=403)

        try:
            data = json.loads(request.body.decode('utf-8'))
            new_text = data.get('text', '').strip()

            if not new_text:
                return JsonResponse({"success": False, "message": "Empty text"}, status=400)

            comment.text = new_text
            comment.save()

            return JsonResponse({"success": True, "text": comment.text})

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class CommentDeleteView(LoginRequiredMixin, View):
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)

        # Check for permissions
        if not (request.user.id == comment.author.id or
                request.user.is_admin or
                request.user.is_moderator):
            return JsonResponse({
                "success": False,
                "message": "You don't have permission to delete this comment."
            })

        Vote.objects.filter(comment=comment).delete()
        comment.delete()
        return JsonResponse({"success": True})

# Vote on comments (like/dislike)
class VoteView(LoginRequiredMixin, View):
    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)
            comment_id = int(data['comment_id'])
            vote_type = data['vote_type']

            comment = get_object_or_404(Comment, id=comment_id)
            vote = Vote.objects.filter(user=request.user, comment=comment).first()

            if vote:
                if vote.vote_type == vote_type:
                    vote.delete()
                else:
                    vote.vote_type = vote_type
                    vote.save()
            else:
                Vote.objects.create(
                    user=request.user,
                    comment=comment,
                    vote_type=vote_type
                )

            comment.likes_count = Vote.objects.filter(comment=comment, vote_type='like').count()
            comment.dislikes_count = Vote.objects.filter(comment=comment, vote_type='dislike').count()
            comment.save()

            return JsonResponse({
                'success': True,
                'likes': comment.likes_count,
                'dislikes': comment.dislikes_count
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)