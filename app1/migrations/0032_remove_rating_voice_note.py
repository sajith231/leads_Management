# Generated by Django 5.1.1 on 2025-02-03 06:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0031_alter_rating_appearance_alter_rating_attitude_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rating',
            name='voice_note',
        ),
    ]
