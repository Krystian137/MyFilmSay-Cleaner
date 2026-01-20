from django.contrib import admin
from django.contrib import admin
from .models import Movie, Comment, Vote

# Register your models here.
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'rating', 'director']
    list_filter = ['date', 'genres']
    search_fields = ['title', 'director', 'writers']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'movie', 'text_preview', 'timestamp', 'likes_count', 'dislikes_count']
    list_filter = ['timestamp', 'movie']
    search_fields = ['text', 'author__name']
    raw_id_fields = ['author', 'movie', 'parent']

    def text_preview(self, obj):
        return obj.text[:50]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'comment', 'vote_type', 'created_at']
    list_filter = ['vote_type', 'created_at']