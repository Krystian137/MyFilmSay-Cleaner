from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    # Lista i wyszukiwanie
    path('', views.MovieListView.as_view(), name='list'),
    path('search/', views.MovieSearchView.as_view(), name='search'),

    # Szczegóły filmu
    path('<int:movie_id>/', views.MovieDetailView.as_view(), name='detail'),

    # CRUD filmów (admin/moderator)
    path('add/', views.MovieCreateView.as_view(), name='create'),
    path('<int:movie_id>/edit/', views.MovieUpdateView.as_view(), name='update'),
    path('<int:movie_id>/delete/', views.MovieDeleteView.as_view(), name='delete'),

    # Import z TMDB
    path('find/', views.FindMovieView.as_view(), name='find'),
    path('import/<int:movie_id>/', views.ImportMovieFromTMDBView.as_view(), name='import'),

    # Komentarze
    path('<int:movie_id>/comment/', views.CommentCreateView.as_view(), name='comment_create'),
    path('comment/<int:comment_id>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),

    # Głosowanie
    path('vote/', views.VoteView.as_view(), name='vote'),

    # AJAX
    path('<int:movie_id>/load-comments/', views.LoadCommentsView.as_view(), name='load_comments'),
]