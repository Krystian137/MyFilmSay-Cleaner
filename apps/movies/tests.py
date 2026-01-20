from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from apps.movies.models import Movie, Comment, Vote
from apps.users.models import RoleEnum
from unittest.mock import patch, Mock
import json

User = get_user_model()

class MovieModelTest(TestCase):
    def test_movie_creation(self):
        movie = Movie.objects.create(
            title="Test Movie",
            date="2023",
            body="Description",
            rating=8.5
        )
        self.assertEqual(str(movie), "Test Movie")
        self.assertEqual(movie.rating, 8.5)

    def test_comment_creation(self):
        user = User.objects.create_user(email='u@ex.com', name='U', password='pw')
        movie = Movie.objects.create(title="M", date="2023")
        comment = Comment.objects.create(
            movie=movie,
            author=user,
            text="Nice",
            user_rating=9.0
        )
        self.assertEqual(str(comment), f"Comment by {user.name} on {movie.title}")
        self.assertFalse(comment.is_reply)

    def test_comment_reply(self):
        user = User.objects.create_user(email='u@ex.com', name='U', password='pw')
        movie = Movie.objects.create(title="M", date="2023")
        parent = Comment.objects.create(movie=movie, author=user, text="Parent", user_rating=8)
        reply = Comment.objects.create(movie=movie, author=user, text="Reply", parent=parent)
        self.assertTrue(reply.is_reply)
        self.assertEqual(reply.parent, parent)

    def test_vote_creation(self):
        user = User.objects.create_user(email='u@ex.com', name='U', password='pw')
        movie = Movie.objects.create(title="M", date="2023")
        comment = Comment.objects.create(movie=movie, author=user, text="C", user_rating=8)
        vote = Vote.objects.create(user=user, comment=comment, vote_type="like")
        self.assertEqual(str(vote), f"{user.email} voted like on comment {comment.id}")

class MovieViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_pass = 'StrongPass123!'
        self.user = User.objects.create_user(email='user@example.com', name='User', password=self.user_pass)
        self.moderator = User.objects.create_user(email='mod@example.com', name='Mod', password=self.user_pass, role=RoleEnum.MODERATOR)
        self.admin = User.objects.create_superuser(email='admin@example.com', name='Admin', password=self.user_pass)

        self.movie = Movie.objects.create(title="Test Movie", date="2023", body="Desc", rating=8.0)

    def test_movie_list(self):
        response = self.client.get(reverse('movies:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")
        self.assertTemplateUsed(response, 'movies/index.html')

    def test_movie_list_sort(self):
        Movie.objects.create(title="A Movie", date="2022", rating=9.0)
        response = self.client.get(reverse('movies:list') + '?sort_by=title')
        self.assertEqual(response.status_code, 200)
        # Check context order?
        movies = response.context['all_movies']
        self.assertEqual(movies[0].title, "A Movie")

    def test_movie_detail(self):
        response = self.client.get(reverse('movies:detail', kwargs={'movie_id': self.movie.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")
        self.assertTemplateUsed(response, 'movies/movie.html')

    def test_movie_search(self):
        response = self.client.get(reverse('movies:search') + '?query=Test')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")

    def test_create_movie_permission(self):
        # User
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.get(reverse('movies:create'))
        self.assertRedirects(response, reverse('movies:list'))

        # Moderator
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.get(reverse('movies:create'))
        self.assertEqual(response.status_code, 200)

    def test_create_movie_post(self):
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:create'), {
            'title': 'New Movie',
            'date': '2024',
            'body': 'Content',
            'rating': 7.5,
            'img_url': 'https://example.com/img.jpg'
        })
        self.assertRedirects(response, reverse('movies:list'))
        self.assertTrue(Movie.objects.filter(title='New Movie').exists())

    def test_update_movie(self):
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:update', kwargs={'movie_id': self.movie.id}), {
            'title': 'Updated Title',
            'date': '2023',
            'body': 'Desc',
            'rating': 8.0
        })
        self.assertRedirects(response, reverse('movies:detail', kwargs={'movie_id': self.movie.id}))
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, 'Updated Title')

    def test_delete_movie(self):
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:delete', kwargs={'movie_id': self.movie.id}))
        self.assertRedirects(response, reverse('movies:list'))
        self.assertFalse(Movie.objects.filter(id=self.movie.id).exists())


class CommentVoteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_pass = 'StrongPass123!'
        self.user = User.objects.create_user(email='user@example.com', name='User', password=self.user_pass)
        self.movie = Movie.objects.create(title="M", date="2023")
        self.comment = Comment.objects.create(movie=self.movie, author=self.user, text="C", user_rating=8)

    def test_add_comment(self):
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:comment_create', kwargs={'movie_id': self.movie.id}), {
            'text': 'Great movie!',
            'user_rating': 9.0
        })
        self.assertRedirects(response, reverse('movies:detail', kwargs={'movie_id': self.movie.id}))
        self.assertTrue(Comment.objects.filter(text='Great movie!').exists())

    def test_add_reply(self):
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:comment_create', kwargs={'movie_id': self.movie.id}), {
            'text': 'Reply!',
            'parent_id': self.comment.id
        })
        self.assertRedirects(response, reverse('movies:detail', kwargs={'movie_id': self.movie.id}))
        reply = Comment.objects.filter(text='Reply!').first()
        self.assertEqual(reply.parent, self.comment)

    def test_delete_comment(self):
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:comment_delete', kwargs={'comment_id': self.comment.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

    def test_vote_like(self):
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:vote'),
                                    data=json.dumps({'comment_id': f"comment-{self.comment.id}", 'vote_type': 'like'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['likes'], 1)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.likes_count, 1)

    def test_load_comments_ajax(self):
        response = self.client.get(reverse('movies:load_comments', kwargs={'movie_id': self.movie.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('html', data)

class TMDBIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_pass = 'StrongPass123!'
        self.moderator = User.objects.create_user(email='mod@example.com', name='Mod', password=self.user_pass, role=RoleEnum.MODERATOR)

    @patch('apps.movies.views.requests.get')
    def test_find_movie(self, mock_get):
        # Mock TMDB response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"id": 123, "title": "Inception", "release_date": "2010-07-16"}]
        }
        mock_get.return_value = mock_response

        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('movies:find'), {'title': 'Inception'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inception")

    @patch('apps.movies.views.requests.get')
    def test_import_movie(self, mock_get):
        # Mock responses for movie details and credits
        def side_effect(url, params):
            if "/credits" in url:
                return Mock(json=lambda: {"crew": [{"job": "Director", "name": "Christopher Nolan"}]})
            else:
                return Mock(json=lambda: {
                    "title": "Inception",
                    "release_date": "2010-07-16",
                    "overview": "Dream...",
                    "vote_average": 8.8,
                    "poster_path": "/poster.jpg",
                    "genres": [{"name": "Sci-Fi"}]
                })

        mock_get.side_effect = side_effect

        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.get(reverse('movies:import', kwargs={'movie_id': 123}))

        # Should redirect to update page
        movie = Movie.objects.get(title="Inception")
        self.assertRedirects(response, reverse('movies:update', kwargs={'movie_id': movie.id}))
        self.assertEqual(movie.director, "Christopher Nolan")
