# Generated by Django 5.1.1 on 2024-11-19 12:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0016_remove_leadrequirementamount_remarks'),
    ]

    operations = [
        migrations.AddField(
            model_name='leadrequirementamount',
            name='remarks',
            field=models.TextField(blank=True, null=True),
        ),
    ]