# Generated by Django 5.1.6 on 2025-05-16 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GOESApp', '0005_cart_created_at_cart_products'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='phone_number',
            field=models.CharField(default=1, max_length=15),
            preserve_default=False,
        ),
    ]
