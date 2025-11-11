# purchase_order/migrations/0007_add_department_logo.py
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('purchase_order', '0006_merge_20251110_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='department',
            name='logo',
            field=models.ImageField(upload_to='department_logos/', null=True, blank=True),
        ),
    ]
