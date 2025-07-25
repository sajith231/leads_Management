# Generated by Django 5.0.2 on 2025-06-30 11:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0186_delete_complaintimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplaintImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='complaint_images/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('complaint_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='app1.servicelogcomplaint')),
            ],
        ),
    ]
