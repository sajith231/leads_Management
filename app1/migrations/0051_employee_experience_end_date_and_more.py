# Generated by Django 5.1.1 on 2025-02-17 07:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0050_delete_experiencecertificate'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='experience_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='employee',
            name='experience_start_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
