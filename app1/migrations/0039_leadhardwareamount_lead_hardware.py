# Generated by Django 5.1.1 on 2024-12-18 11:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0038_hardware'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeadHardwareAmount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('hardware', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app1.hardware')),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hardware_amounts', to='app1.lead')),
            ],
            options={
                'unique_together': {('lead', 'hardware')},
            },
        ),
        migrations.AddField(
            model_name='lead',
            name='hardware',
            field=models.ManyToManyField(through='app1.LeadHardwareAmount', to='app1.hardware'),
        ),
    ]
