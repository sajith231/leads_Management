# Generated by Django 5.1.1 on 2024-12-16 07:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0029_location'),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='areas', to='app1.district')),
            ],
            options={
                'ordering': ['name'],
                'unique_together': {('name', 'district')},
            },
        ),
        migrations.DeleteModel(
            name='Location',
        ),
    ]