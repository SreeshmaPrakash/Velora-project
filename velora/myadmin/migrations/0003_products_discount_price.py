# Generated by Django 5.1.5 on 2025-01-28 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myadmin', '0002_alter_productimage_options_productimage_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='products',
            name='discount_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
