# Generated by Django 5.1.1 on 2024-11-12 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0004_softwareamount'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='software_amounts',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.DeleteModel(
            name='SoftwareAmount',
        ),
    ]
