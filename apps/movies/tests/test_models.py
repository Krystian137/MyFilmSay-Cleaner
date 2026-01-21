from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from apps.movies.models import Movie, Comment, Vote
from apps.users.models import User

class MovieModelTest(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title="Test Movie",
            date="2023",
            body="Test Description",
            rating=8.5
        )

    def test_movie_creation(self):
        """Test that a movie instance is correctly created."""
        self.assertEqual(self.movie.title, "Test Movie")
        self.assertEqual(self.movie.date, "2023")
        self.assertEqual(self.movie.rating, 8.5)

    def test_slug_generation(self):
        """Test that slug is automatically generated from title."""
        self.assertEqual(self.movie.slug, "test-movie")

    def test_string_representation(self):
        """Test the string representation of the movie."""
        self.assertEqual(str(self.movie), "Test Movie")

    def test_rating_validation(self):
        """Test rating validation (0-10)."""
        movie = Movie(
            title="Invalid Rating Movie",
            date="2023",
            body="Desc",
            rating=11.0 # Invalid
        )
        # Note: Validators are not run automatically on save(), need full_clean()
        with self.assertRaises(ValidationError):
            movie.full_clean()

class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            name="Test User",
            password="password123"
        )
        self.movie = Movie.objects.create(
            title="Test Movie",
            date="2023",
            body="Description"
        )
        self.comment = Comment.objects.create(
            movie=self.movie,
            author=self.user,
            text="Great movie!",
            user_rating=9.0
        )

    def test_comment_creation(self):
        """Test comment creation and relationships."""
        self.assertEqual(self.comment.text, "Great movie!")
        self.assertEqual(self.comment.author, self.user)
        self.assertEqual(self.comment.movie, self.movie)
        self.assertFalse(self.comment.is_reply)

    def test_reply_creation(self):
        """Test creating a reply to a comment."""
        reply = Comment.objects.create(
            movie=self.movie,
            author=self.user,
            text="I agree!",
            parent=self.comment
        )
        self.assertTrue(reply.is_reply)
        self.assertEqual(reply.parent, self.comment)
        self.assertIn(reply, self.comment.replies.all())

    def test_string_representation(self):
        """Test string representation of comment."""
        expected_str = f"Comment by {self.user.name} on {self.movie.title}"
        self.assertEqual(str(self.comment), expected_str)

class VoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="voter@example.com",
            name="Voter",
            password="password"
        )
        self.movie = Movie.objects.create(title="Movie", body="Desc")
        self.comment = Comment.objects.create(
            movie=self.movie,
            author=self.user,
            text="Vote this",
            user_rating=5.0
        )

    def test_vote_creation(self):
        """Test creating a vote."""
        vote = Vote.objects.create(
            user=self.user,
            comment=self.comment,
            vote_type="like"
        )
        self.assertEqual(vote.vote_type, "like")

    def test_unique_vote_constraint(self):
        """Test that a user cannot vote twice on the same comment."""
        Vote.objects.create(
            user=self.user,
            comment=self.comment,
            vote_type="like"
        )
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                user=self.user,
                comment=self.comment,
                vote_type="dislike"
            )
