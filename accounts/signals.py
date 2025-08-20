from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Role


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created and not instance.role_id:
        default_role, _ = Role.objects.get_or_create(
            name="user", defaults={"description": "Regular user"}
        )
        instance.role = default_role
        instance.save()
