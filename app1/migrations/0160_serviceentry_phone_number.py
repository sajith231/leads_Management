# Generated by Django 5.0.2 on 2025-05-15 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0159_serviceentry_duration'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceentry',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
