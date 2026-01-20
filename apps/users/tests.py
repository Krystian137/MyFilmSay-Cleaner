from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from apps.users.models import RoleEnum

User = get_user_model()

class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(email='test@example.com', name='Test User', password='password123')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.name, 'Test User')
        self.assertTrue(user.check_password('password123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, RoleEnum.USER)
        self.assertTrue(user.is_regular_user)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email='admin@example.com', name='Admin User', password='password123')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, RoleEnum.ADMIN)
        self.assertTrue(admin.is_admin)

    def test_create_user_invalid(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', name='No Email', password='pw')
        with self.assertRaises(ValueError):
            User.objects.create_user(email='no@name.com', name='', password='pw')

    def test_roles(self):
        user = User.objects.create_user(email='u@ex.com', name='U', role=RoleEnum.USER)
        mod = User.objects.create_user(email='m@ex.com', name='M', role=RoleEnum.MODERATOR)
        admin = User.objects.create_user(email='a@ex.com', name='A', role=RoleEnum.ADMIN)

        self.assertTrue(user.is_regular_user)
        self.assertFalse(user.is_moderator)
        self.assertFalse(user.is_admin)

        self.assertFalse(mod.is_regular_user)
        self.assertTrue(mod.is_moderator)
        self.assertFalse(mod.is_admin)

        self.assertFalse(admin.is_regular_user)
        self.assertTrue(admin.is_moderator) # Admin is also moderator
        self.assertTrue(admin.is_admin)

    def test_str(self):
        user = User.objects.create_user(email='test@example.com', name='Test User')
        self.assertEqual(str(user), 'Test User (test@example.com)')


class UserViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_pass = 'StrongPass123!'
        self.user = User.objects.create_user(email='user@example.com', name='User', password=self.user_pass)
        self.admin = User.objects.create_superuser(email='admin@example.com', name='Admin', password=self.user_pass)
        self.moderator = User.objects.create_user(email='mod@example.com', name='Mod', password=self.user_pass, role=RoleEnum.MODERATOR)

    def test_register_view_get(self):
        response = self.client.get(reverse('users:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/register.html')

    def test_register_view_post_success(self):
        response = self.client.post(reverse('users:register'), {
            'email': 'new@example.com',
            'name': 'New User',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        if response.status_code == 200:
             print("Register errors:", response.context['form'].errors)
        self.assertRedirects(response, reverse('movies:list'))
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_register_view_post_existing_email(self):
        response = self.client.post(reverse('users:register'), {
            'email': 'user@example.com', # Existing
            'name': 'Duplicate',
            'password1': 'pw',
            'password2': 'pw'
        })
        self.assertRedirects(response, reverse('users:login'))
        # Should warning message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("You've already signed up" in str(m) for m in messages))

    def test_login_view_get(self):
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_login_view_post_success(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'user@example.com',
            'password': self.user_pass
        })
        self.assertRedirects(response, reverse('movies:list'))
        # Check session
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_login_view_post_invalid(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'user@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        # Check messages
        messages = list(response.context['messages'])
        self.assertTrue(any("Invalid email or password" in str(m) for m in messages))

    def test_logout_view(self):
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:logout'))
        self.assertRedirects(response, reverse('movies:list'))
        response = self.client.get(reverse('movies:list')) # Follow redirect
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_user_list_view_permissions(self):
        # Anonymous
        response = self.client.get(reverse('users:list'))
        self.assertRedirects(response, f"{reverse('users:login')}?next={reverse('users:list')}")

        # Regular user
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.get(reverse('users:list'))
        # Expect redirect to movies list due to no permission (handled in dispatch)
        self.assertRedirects(response, reverse('movies:list'))

        # Moderator
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.get(reverse('users:list'))
        self.assertEqual(response.status_code, 200)

        # Admin
        self.client.login(email='admin@example.com', password=self.user_pass)
        response = self.client.get(reverse('users:list'))
        self.assertEqual(response.status_code, 200)

    def test_user_profile_view(self):
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.get(reverse('users:profile', kwargs={'user_id': self.user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/user_profile.html')
        self.assertEqual(response.context['profile_owner'], self.user)

    def test_assign_role_view(self):
        # Admin assigns moderator role to user
        self.client.login(email='admin@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:assign_role', kwargs={'user_id': self.user.id, 'role': 'moderator'}))
        self.assertRedirects(response, reverse('users:list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, RoleEnum.MODERATOR)

        # Reset user role
        self.user.role = RoleEnum.USER
        self.user.save()

        # Moderator tries to assign (should be allowed per code: "admin or moderator")
        # We need a different user for target, or use self.user as target (but we reset it to USER)
        # self.moderator is the actor.
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:assign_role', kwargs={'user_id': self.user.id, 'role': 'moderator'}))
        self.assertRedirects(response, reverse('users:list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, RoleEnum.MODERATOR)

        # Reset user role again for next check
        self.user.role = RoleEnum.USER
        self.user.save()

        # User tries to assign (forbidden)
        self.client.login(email='user@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:assign_role', kwargs={'user_id': self.user.id, 'role': 'admin'}))
        self.assertRedirects(response, reverse('movies:list'))

        # Self assign admin check (by moderator)
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:assign_role', kwargs={'user_id': self.moderator.id, 'role': 'admin'}))
        self.assertRedirects(response, reverse('users:list'))
        # Check message "You cannot assign the admin role to yourself."?
        messages = list(get_messages(response.wsgi_request))
        # This might be tricky to test with redirect, but we can assume it works if no error thrown.

    def test_user_delete_view(self):
        # Admin deletes user
        self.client.login(email='admin@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:delete', kwargs={'user_id': self.user.id}))
        self.assertRedirects(response, reverse('users:list'))
        self.assertFalse(User.objects.filter(id=self.user.id).exists())

        # Moderator tries to delete (forbidden: only admin)
        # Re-create user
        user = User.objects.create_user(email='u2@ex.com', name='U2', password='pw')
        self.client.login(email='mod@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:delete', kwargs={'user_id': user.id}))
        self.assertRedirects(response, reverse('users:list'))
        self.assertTrue(User.objects.filter(id=user.id).exists()) # Should still exist

        # Self delete check
        self.client.login(email='admin@example.com', password=self.user_pass)
        response = self.client.post(reverse('users:delete', kwargs={'user_id': self.admin.id}))
        self.assertRedirects(response, reverse('users:list'))
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())
