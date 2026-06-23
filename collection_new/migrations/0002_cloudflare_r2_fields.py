"""
Auto-generated migration for Collection model Cloudflare R2 fields.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection_new', '0003_collection_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='cloudflare_r2_url',
            field=models.URLField(blank=True, help_text='Cloudflare R2 public URL for the payment proof', null=True),
        ),
        migrations.AddField(
            model_name='collection',
            name='cloudflare_r2_key',
            field=models.CharField(blank=True, help_text='Cloudflare R2 S3 object key for deletion', max_length=500, null=True),
        ),
    ]
