# Generated by Django 5.1.1 on 2025-03-04 05:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0073_rating_added_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rating',
            name='added_by',
        ),
    ]
