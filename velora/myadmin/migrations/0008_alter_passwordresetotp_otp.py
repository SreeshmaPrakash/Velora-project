# Generated by Django 5.1.5 on 2025-02-03 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myadmin', '0007_passwordresetotp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passwordresetotp',
            name='otp',
            field=models.CharField(max_length=4),
        ),
    ]
