# Generated by Django 5.1.7 on 2025-03-12 13:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_profile_avatar_style'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='avatar_style',
        ),
    ]
