# Generated by Django 5.1.6 on 2025-05-11 16:26

import GOESApp.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GOESApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='in_stock',
            field=models.PositiveIntegerField(default=0, help_text='Number of items in stock'),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(default=GOESApp.models.get_default_category, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='GOESApp.category'),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='product_images/'),
        ),
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
