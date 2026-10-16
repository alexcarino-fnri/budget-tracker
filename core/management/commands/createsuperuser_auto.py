import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Automatically creates or updates a superuser from environment variables without requiring shell access.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD not set. Skipping automatic superuser creation.'
            ))
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )

        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if email:
            user.email = email
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' password and permissions updated successfully."))
