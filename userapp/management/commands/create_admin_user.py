from django.core.management.base import BaseCommand
from userapp.models import User


class Command(BaseCommand):
    help = 'Create the bank admin user with predefined credentials'

    def handle(self, *args, **kwargs):
        # Admin user credentials
        admin_email = 'philos@gmail.com'
        admin_password = 'philos@48'
        admin_first_name = 'Bank'
        admin_last_name = 'Admin'
        
        # Check if admin user already exists
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                'first_name': admin_first_name,
                'last_name': admin_last_name,
                'full_name': f'{admin_first_name} {admin_last_name}',
                'user_type': User.ADMIN,
                'is_active': True,
                'is_staff': True,
                'is_admin': True,
            }
        )
        
        if created:
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Successfully created bank admin user: {admin_email}'
            ))
        else:
            # Update existing admin user with correct properties
            admin_user.first_name = admin_first_name
            admin_user.last_name = admin_last_name
            admin_user.full_name = f'{admin_first_name} {admin_last_name}'
            admin_user.user_type = User.ADMIN
            admin_user.is_active = True
            admin_user.is_staff = True
            admin_user.is_admin = True
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Updated existing bank admin user: {admin_email}'
            ))