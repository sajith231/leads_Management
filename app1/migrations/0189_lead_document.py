# Generated by Django 5.0.2 on 2025-07-24 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0188_servicelogcomplaint_completed_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='document',
            field=models.FileField(blank=True, null=True, upload_to='lead_documents/'),
        ),
    ]
