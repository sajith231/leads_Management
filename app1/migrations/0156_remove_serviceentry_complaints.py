# Generated by Django 5.0.2 on 2025-05-15 12:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0155_serviceentry_complaint'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='serviceentry',
            name='complaints',
        ),
    ]
