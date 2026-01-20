from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('', views.UserListView.as_view(), name='list'),
    path('<int:user_id>/', views.UserProfileView.as_view(), name='profile'),
    path('<int:user_id>/assign-role/<str:role>/', views.AssignRoleView.as_view(), name='assign_role'),
    path('<int:user_id>/delete/', views.UserDeleteView.as_view(), name='delete'),
]