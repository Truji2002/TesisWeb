# Generated by Django 4.2 on 2024-11-10 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('globalqhse', '0027_alter_modulo_archivo'),
    ]

    operations = [
        migrations.AddField(
            model_name='curso',
            name='imagen',
            field=models.ImageField(null=True, upload_to='documents/'),
        ),
    ]
