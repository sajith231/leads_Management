# Generated by Django 5.0.2 on 2025-06-30 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0181_servicelogcomplaint_assigned_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicelogcomplaint',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='complaint_images/'),
        ),
    ]
