# Generated by Django 5.1.1 on 2024-11-04 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0012_lead'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='follow_up_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='lead',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='lead_images/'),
        ),
        migrations.AddField(
            model_name='lead',
            name='quotation_required',
            field=models.BooleanField(default=False),
        ),
    ]