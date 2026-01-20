from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Movie(models.Model):
    title = models.CharField(max_length=250, unique=True, verbose_name="Movie Title")
    date = models.CharField(max_length=10, verbose_name="Release Date")
    body = models.TextField(verbose_name="Description")
    img_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Image URL")
    rating = models.FloatField(blank=True, null=True, verbose_name="Average Rating",validators=[MinValueValidator(0.0),
                                                                                                MaxValueValidator(10.0)])
    director = models.CharField(max_length=250, blank=True, null=True, verbose_name="Director")
    writers = models.TextField(blank=True, null=True, verbose_name="Writers")
    genres = models.CharField(max_length=250, blank=True, null=True, verbose_name="Genres")
    slug = models.SlugField(unique=True, blank=True, verbose_name="Slug")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Movie"
        verbose_name_plural = "Movies"

    def __str__(self):
        return self.title


class Comment(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="comments", verbose_name="Movie")
    author = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="comments", verbose_name="Author")
    text = models.TextField(verbose_name="Comment Text")
    user_rating = models.FloatField(blank=True, null=True, verbose_name="User Rating", validators=[MinValueValidator(0.0),
                                                                                                   MaxValueValidator(10.0)])
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="replies",
                               verbose_name="Parent Comment")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    likes_count = models.IntegerField(default=0, verbose_name="Likes Count")
    dislikes_count = models.IntegerField(default=0, verbose_name="Dislikes Count")

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['movie', 'timestamp']),
            models.Index(fields=['author']),
        ]

    def __str__(self):
        return f"Comment by {self.author.name} on {self.movie.title}"

    @property
    def is_reply(self):
        return self.parent is not None


class Vote(models.Model):
    VOTE_CHOICES = [
        ("like", "Like"),
        ("dislike", "Dislike"),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="votes", verbose_name="User")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="votes", verbose_name="Comment")
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES, verbose_name="Vote Type")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vote"
        verbose_name_plural = "Votes"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'comment'],
                name='unique_user_comment_vote'
            ),
        ]
        indexes = [
            models.Index(fields=['comment', 'vote_type']),
        ]

    def __str__(self):
        return f"{self.user.email} voted {self.vote_type} on comment {self.comment.id}"