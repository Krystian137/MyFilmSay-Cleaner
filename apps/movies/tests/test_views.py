import json
from django.test import TestCase, Client
from django.urls import reverse
from apps.movies.models import Movie, Comment, Vote
from apps.users.models import User, RoleEnum

class BaseViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Users
        self.admin = User.objects.create_user(email="admin@example.com", name="Admin", password="password", role=RoleEnum.ADMIN)
        self.moderator = User.objects.create_user(email="mod@example.com", name="Mod", password="password", role=RoleEnum.MODERATOR)
        self.user = User.objects.create_user(email="user@example.com", name="User", password="password", role=RoleEnum.USER)
        self.user2 = User.objects.create_user(email="user2@example.com", name="User2", password="password", role=RoleEnum.USER)

        # Create Movie
        self.movie = Movie.objects.create(
            title="Test Movie",
            date="2023",
            body="Description",
            rating=8.0,
            director="Director",
            genres="Action"
        )

        # Create Comment
        self.comment = Comment.objects.create(
            movie=self.movie,
            author=self.user,
            text="First comment",
            user_rating=9.0
        )

class MovieViewTest(BaseViewTest):
    def test_movie_list_view(self):
        """Test movie list page loads correctly."""
        response = self.client.get(reverse('movies:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")
        self.assertTemplateUsed(response, 'movies/movie_list.html')

    def test_movie_search(self):
        """Test movie search functionality."""
        response = self.client.get(reverse('movies:search'), {'query': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")

        response = self.client.get(reverse('movies:search'), {'query': 'Nonexistent'})
        self.assertNotContains(response, "Test Movie")

    def test_movie_detail_view(self):
        """Test movie detail page loads correctly."""
        response = self.client.get(reverse('movies:detail', args=[self.movie.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Movie")
        self.assertContains(response, "First comment") # Check if comment is rendered

    def test_create_movie_permission(self):
        """Test only admin/mod can create movies."""
        # Anonymous
        response = self.client.get(reverse('movies:create'))
        self.assertNotEqual(response.status_code, 200) # Should redirect or forbidden

        # Regular User
        self.client.login(email="user@example.com", password="password")
        response = self.client.get(reverse('movies:create'))
        self.assertRedirects(response, reverse('movies:list')) # PermissionMixin redirects to list

        # Moderator
        self.client.login(email="mod@example.com", password="password")
        response = self.client.get(reverse('movies:create'))
        self.assertEqual(response.status_code, 200)

        # Admin
        self.client.login(email="admin@example.com", password="password")
        response = self.client.get(reverse('movies:create'))
        self.assertEqual(response.status_code, 200)

    def test_create_movie_post(self):
        """Test creating a movie."""
        self.client.login(email="admin@example.com", password="password")
        response = self.client.post(reverse('movies:create'), {
            'title': 'New Movie',
            'date': '2024',
            'body': 'New Description',
            'rating': 9.0
        })
        self.assertEqual(Movie.objects.count(), 2)
        new_movie = Movie.objects.get(title='New Movie')
        self.assertRedirects(response, reverse('movies:list')) # View redirects to list on success

    def test_update_movie_permission(self):
        """Test only admin/mod can update movies."""
        url = reverse('movies:update', args=[self.movie.slug])

        # Regular User
        self.client.login(email="user@example.com", password="password")
        response = self.client.get(url)
        self.assertRedirects(response, reverse('movies:list'))

        # Admin
        self.client.login(email="admin@example.com", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_delete_movie(self):
        """Test deleting a movie."""
        self.client.login(email="admin@example.com", password="password")
        response = self.client.post(reverse('movies:delete', args=[self.movie.slug]))
        self.assertRedirects(response, reverse('movies:list'))
        self.assertEqual(Movie.objects.count(), 0)

class CommentViewTest(BaseViewTest):
    def test_add_comment(self):
        """Test adding a comment."""
        self.client.login(email="user@example.com", password="password")
        url = reverse('movies:comment_create', args=[self.movie.id])

        # Success
        response = self.client.post(url, {
            'text': 'New Comment',
            'user_rating': 8.0
        })
        self.assertRedirects(response, reverse('movies:detail', args=[self.movie.slug]))
        self.assertEqual(Comment.objects.count(), 2)

        # Fail: Missing rating for main comment
        response = self.client.post(url, {
            'text': 'No Rating',
        })
        # Expect redirect back to detail with error message (implementation uses messages)
        self.assertRedirects(response, reverse('movies:detail', args=[self.movie.slug]))
        self.assertEqual(Comment.objects.count(), 2)

    def test_add_reply(self):
        """Test adding a reply (no rating needed)."""
        self.client.login(email="user@example.com", password="password")
        url = reverse('movies:comment_create', args=[self.movie.id])

        response = self.client.post(url, {
            'text': 'Reply',
            'parent_id': self.comment.id
        })
        self.assertRedirects(response, reverse('movies:detail', args=[self.movie.slug]))
        self.assertEqual(Comment.objects.count(), 2) # Should be 2 now
        reply = Comment.objects.last()
        self.assertTrue(reply.is_reply)
        self.assertEqual(reply.parent, self.comment)

    def test_comment_edit_permission(self):
        """Test comment editing permissions."""
        url = reverse('movies:comment_edit', args=[self.comment.id])
        data = json.dumps({'text': 'Edited Text'})

        # Non-owner
        self.client.login(email="user2@example.com", password="password")
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 403)

        # Owner
        self.client.login(email="user@example.com", password="password")
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, 'Edited Text')

    def test_comment_delete_permission(self):
        """Test comment deletion permissions."""
        url = reverse('movies:comment_delete', args=[self.comment.id])

        # Non-owner
        self.client.login(email="user2@example.com", password="password")
        response = self.client.post(url)
        self.assertEqual(response.json()['success'], False)

        # Owner
        self.client.login(email="user@example.com", password="password")
        response = self.client.post(url)
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(Comment.objects.count(), 0)

    def test_moderator_can_delete_comment(self):
        """Test moderator can delete any comment."""
        url = reverse('movies:comment_delete', args=[self.comment.id])
        self.client.login(email="mod@example.com", password="password")
        response = self.client.post(url)
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(Comment.objects.count(), 0)

class VoteViewTest(BaseViewTest):
    def test_vote_like(self):
        """Test liking a comment."""
        self.client.login(email="user2@example.com", password="password")
        url = reverse('movies:vote')
        data = json.dumps({
            'comment_id': self.comment.id,
            'vote_type': 'like'
        })

        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['likes'], 1)

        self.comment.refresh_from_db()
        self.assertEqual(self.comment.likes_count, 1)
        self.assertTrue(Vote.objects.filter(user=self.user2, comment=self.comment, vote_type='like').exists())

    def test_vote_toggle(self):
        """Test toggling a like (liking twice removes the like)."""
        self.client.login(email="user2@example.com", password="password")
        url = reverse('movies:vote')
        data = json.dumps({'comment_id': self.comment.id, 'vote_type': 'like'})

        # First like
        self.client.post(url, data, content_type='application/json')

        # Second like (toggle off)
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.json()['likes'], 0)
        self.assertFalse(Vote.objects.filter(user=self.user2, comment=self.comment).exists())

    def test_vote_change(self):
        """Test changing from like to dislike."""
        self.client.login(email="user2@example.com", password="password")
        url = reverse('movies:vote')

        # Like
        self.client.post(url, json.dumps({'comment_id': self.comment.id, 'vote_type': 'like'}), content_type='application/json')

        # Dislike
        response = self.client.post(url, json.dumps({'comment_id': self.comment.id, 'vote_type': 'dislike'}), content_type='application/json')

        self.assertEqual(response.json()['likes'], 0)
        self.assertEqual(response.json()['dislikes'], 1)

        vote = Vote.objects.get(user=self.user2, comment=self.comment)
        self.assertEqual(vote.vote_type, 'dislike')
