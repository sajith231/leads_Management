# Generated by Django 5.1.1 on 2025-02-08 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0039_businesstype'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='firm_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='agent',
            name='remarks',
            field=models.TextField(blank=True),
        ),
    ]
