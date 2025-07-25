# Generated by Django 5.0.2 on 2025-07-22 04:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0187_complaintimage'),
        ('app2', '0046_alter_credentialdetail_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='feeder',
            name='module_prices',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='feeder',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('under_process', 'Under Process')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='feeder',
            name='branch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app1.branch'),
        ),
        migrations.AlterField(
            model_name='feeder',
            name='nature',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app1.businesstype'),
        ),
    ]
