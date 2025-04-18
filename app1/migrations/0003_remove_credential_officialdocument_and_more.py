# Generated by Django 5.1.1 on 2025-01-25 04:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0002_credential_officialdocument_alter_credential_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='credential',
            name='officialdocument',
        ),
        migrations.AlterField(
            model_name='credential',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.CreateModel(
            name='DocumentCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(blank=True, null=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='attachments/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('credential', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app1.credential')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app1.officialdocument')),
            ],
        ),
        migrations.DeleteModel(
            name='CredentialDetail',
        ),
    ]
