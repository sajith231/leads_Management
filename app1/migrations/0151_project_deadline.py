# Generated by Django 5.0.2 on 2025-05-15 06:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0150_alter_cv_district'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='deadline',
            field=models.DateField(blank=True, null=True),
        ),
    ]
