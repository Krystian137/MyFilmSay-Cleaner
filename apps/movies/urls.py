from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.MovieListView.as_view(), name='list'),
    path('search/', views.MovieSearchView.as_view(), name='search'),
    path('add/', views.MovieCreateView.as_view(), name='create'),
    path('find/', views.FindMovieView.as_view(), name='find'),
    path('import/<int:movie_id>/', views.ImportMovieFromTMDBView.as_view(), name='import'),
    path('comment/<int:comment_id>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    path('comment/<int:comment_id>/edit/', views.CommentEditView.as_view(), name='comment_edit'),
    path('vote/', views.VoteView.as_view(), name='vote'),
    path('<int:movie_id>/comment/', views.CommentCreateView.as_view(), name='comment_create'),
    path('<slug:slug>/', views.MovieDetailView.as_view(), name='detail'),
    path('<slug:slug>/edit/', views.MovieUpdateView.as_view(), name='update'),
    path('<slug:slug>/delete/', views.MovieDeleteView.as_view(), name='delete'),
]