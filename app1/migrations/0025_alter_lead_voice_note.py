# Generated by Django 5.1.1 on 2024-12-14 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0024_lead_voice_note'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='voice_note',
            field=models.FileField(blank=True, null=True, upload_to='voice_notes/'),
        ),
    ]
