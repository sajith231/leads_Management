# Generated by Django 5.1.1 on 2025-04-09 04:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0127_laterequest_viewed_by_admin_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='laterequest',
            name='viewed_by_admin',
        ),
        migrations.RemoveField(
            model_name='laterequest',
            name='viewed_by_user',
        ),
        migrations.RemoveField(
            model_name='leaverequest',
            name='viewed_by_admin',
        ),
        migrations.RemoveField(
            model_name='leaverequest',
            name='viewed_by_user',
        ),
    ]
