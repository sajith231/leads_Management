# Generated by Django 5.1.1 on 2025-02-15 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0047_alter_employee_education_alter_employee_experience'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
