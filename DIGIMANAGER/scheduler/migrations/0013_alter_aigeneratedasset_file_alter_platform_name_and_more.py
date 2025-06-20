# Generated by Django 5.1.9 on 2025-06-17 10:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0012_post_generated_caption_by_post_generated_image_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aigeneratedasset',
            name='file',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
        migrations.AlterField(
            model_name='platform',
            name='name',
            field=models.CharField(choices=[('facebook', 'Facebook'), ('instagram', 'Instagram'), ('twitter', 'Twitter (X)'), ('linkedin', 'LinkedIn')], default='instagram', max_length=50),
        ),
        migrations.AlterField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
