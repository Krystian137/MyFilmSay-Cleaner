import os
import django
from django.contrib.auth.hashers import make_password

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import User, RoleEnum

admin_user = User(
    email="admin1@admin.com",
    password=make_password("Admin1"),
    name="Admin1",
    role=RoleEnum.ADMIN
)
admin_user.save()

print("Admin created!")
