# Generated by Django 5.0.2 on 2025-07-10 04:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app2', '0036_socialmediaprojectassignment_deadline'),
    ]

    operations = [
        migrations.AddField(
            model_name='socialmediaprojectassignment',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('started', 'Started'), ('completed', 'Completed'), ('hold', 'Hold')], default='pending', max_length=20),
        ),
    ]
