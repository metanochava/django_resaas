from django.contrib.auth.models import Group
def profile_creator(profiles = []):
    for g in profiles:
        grupo, _ = Group.objects.get_or_create(
            name=g
        )