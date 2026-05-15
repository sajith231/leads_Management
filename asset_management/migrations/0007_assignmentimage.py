import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asset_management', '0006_assignmentreturnimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(help_text='Photo uploaded at time of assignment.', upload_to='assignments/attachments/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_images', to='asset_management.assignment')),
            ],
            options={
                'verbose_name': 'Assignment Image',
                'verbose_name_plural': 'Assignment Images',
                'ordering': ['uploaded_at'],
            },
        ),
    ]
