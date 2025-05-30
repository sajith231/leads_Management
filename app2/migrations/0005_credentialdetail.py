# Generated by Django 5.0.2 on 2025-05-06 08:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app2', '0004_credentials'),
    ]

    operations = [
        migrations.CreateModel(
            name='CredentialDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=255)),
                ('credential', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='details', to='app2.credentials')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app2.field')),
            ],
        ),
    ]
