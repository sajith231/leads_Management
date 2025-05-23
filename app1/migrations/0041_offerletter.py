# Generated by Django 5.1.1 on 2025-02-12 09:54

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0040_agent_firm_name_agent_remarks'),
    ]

    operations = [
        migrations.CreateModel(
            name='OfferLetter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.CharField(blank=True, max_length=255, null=True)),
                ('department', models.CharField(blank=True, max_length=255, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('salary', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('cv', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offer_letters', to='app1.cv')),
            ],
        ),
    ]
