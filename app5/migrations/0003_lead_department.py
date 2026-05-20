import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app5', '0002_customer_taxmaster_lead_created_by_and_more'),
        ('purchase_order', '0003_alter_item_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='leads',
                to='purchase_order.department',
            ),
        ),
    ]
