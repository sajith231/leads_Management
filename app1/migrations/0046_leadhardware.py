# Generated by Django 5.1.1 on 2024-12-19 10:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0045_lead_hardwares'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeadHardware',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('custom_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('hardware', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app1.hardware')),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lead_hardware', to='app1.lead')),
            ],
            options={
                'unique_together': {('lead', 'hardware')},
            },
        ),
    ]