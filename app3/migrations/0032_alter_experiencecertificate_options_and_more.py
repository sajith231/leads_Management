# Generated by Django 5.2.3 on 2025-06-30 05:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app3', '0031_experiencecertificate_end_date_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='experiencecertificate',
            options={'ordering': ['-added_on'], 'verbose_name': 'Experience Certificate', 'verbose_name_plural': 'Experience Certificates'},
        ),
        migrations.AlterField(
            model_name='experiencecertificate',
            name='end_date',
            field=models.DateField(blank=True, help_text='Experience end date', null=True),
        ),
        migrations.AlterField(
            model_name='experiencecertificate',
            name='experience_details',
            field=models.TextField(blank=True, help_text='Additional experience details', null=True),
        ),
        migrations.AlterField(
            model_name='experiencecertificate',
            name='start_date',
            field=models.DateField(blank=True, help_text='Experience start date (usually joining date)', null=True),
        ),
    ]
