# Generated by Django 5.0.2 on 2025-05-26 07:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0164_remove_complaint_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app1.user'),
        ),
    ]
