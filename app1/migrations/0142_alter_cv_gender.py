# Generated by Django 5.0.2 on 2025-05-09 04:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0141_cv_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cv',
            name='gender',
            field=models.CharField(blank=True, choices=[('', ''), ('M', 'Male'), ('F', 'Female')], max_length=1),
        ),
    ]
