# Generated by Django 5.1.1 on 2024-11-12 11:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0007_softwareamount'),
    ]

    operations = [
        migrations.AddField(
            model_name='softwareamount',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='softwareamount',
            name='lead',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='software_amounts', to='app1.lead'),
        ),
    ]
