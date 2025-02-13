# Generated by Django 5.1.5 on 2025-02-01 18:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myadmin', '0005_alter_order_order_number_alter_order_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='myadmin.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myadmin.products')),
            ],
        ),
    ]
