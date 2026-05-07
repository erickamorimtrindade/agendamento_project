from django.db import migrations
import os

def create_superuser(apps, schema_editor):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email    = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

    if username and password and not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)

class Migration(migrations.Migration):
    dependencies = [
        ('agendamento', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_superuser, migrations.RunPython.noop),
    ]