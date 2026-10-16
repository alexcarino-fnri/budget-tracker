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

        # Automatically seed initial loans and bills if requested or not yet seeded
        seed_data = os.environ.get('SEED_INITIAL_DATA', 'True').lower() in ('true', '1', 't')
        if seed_data:
            from django.core.management import call_command
            from debts.models import Debt
            if not Debt.objects.filter(user=user).exists():
                self.stdout.write(f"Seeding initial loans and monthly bills for {username}...")
                call_command('seed_loans', username=username)
