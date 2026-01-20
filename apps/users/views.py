from django.contrib.auth import login, logout
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.db.models import Prefetch
from .models import User, RoleEnum
from .forms import RegisterForm, LoginForm
from apps.movies.models import Comment


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('movies:list')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(self.request, f"Welcome, {user.name}!")
        return redirect(self.success_url)


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('movies:list')

    def form_valid(self, form):
        messages.success(self.request, f"Welcome, {form.get_user().name}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid email or password.")
        return super().form_invalid(form)


class UserLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('movies:list')


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'all_users'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_moderator):
            messages.error(request, "You don't have permission to view this page.")
            return redirect('movies:list')
        return super().dispatch(request, *args, **kwargs)


class UserProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_profile.html'
    context_object_name = 'profile_owner'
    pk_url_kwarg = 'user_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        comments = Comment.objects.filter(
            author=self.object
        ).select_related('movie', 'author').prefetch_related(
            Prefetch('replies', queryset=Comment.objects.select_related('author'))
        )

        user_comments = {}
        for comment in comments:
            movie = comment.movie
            if movie not in user_comments:
                user_comments[movie] = {
                    'comments': [],
                    'replies': {}
                }

            if comment.parent is None:
                user_comments[movie]['comments'].append(comment)
            else:
                parent_id = comment.parent.id
                if parent_id not in user_comments[movie]['replies']:
                    user_comments[movie]['replies'][parent_id] = []
                user_comments[movie]['replies'][parent_id].append(comment)

        context['user_comments'] = user_comments
        return context


class AssignRoleView(LoginRequiredMixin, View):
    def post(self, request, user_id, role):
        if not (request.user.is_admin or request.user.is_moderator):
            messages.error(request, "You don't have permission to assign roles.")
            return redirect('movies:list')

        user = get_object_or_404(User, pk=user_id)

        valid_roles = [RoleEnum.USER.value, RoleEnum.MODERATOR.value, RoleEnum.ADMIN.value]
        if role not in valid_roles:
            messages.error(request, "Invalid role.")
            return redirect('users:list')

        if role == RoleEnum.ADMIN.value and request.user.id == user.id:
            messages.error(request, "You cannot assign the admin role to yourself.")
            return redirect('users:list')

        user.role = role
        user.save()
        messages.success(request, f"Role '{role}' assigned to {user.name}.")
        return redirect('users:list')


class UserDeleteView(LoginRequiredMixin, View):

    def post(self, request, user_id):
        if not request.user.is_admin:
            messages.error(request, "You don't have permission to delete users.")
            return redirect('users:list')

        user = get_object_or_404(User, id=user_id)

        if request.user.id == user.id:
            messages.error(request, "You cannot delete your own account.")
            return redirect('users:list')

        user.delete()
        messages.success(request, f"User {user.name} has been deleted.")
        return redirect('users:list')