# Generated by Django 4.2 on 2024-08-29 03:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('globalqhse', '0002_alter_usuario_estado'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='administrador',
            options={'verbose_name_plural': 'Administradores'},
        ),
        migrations.AlterModelOptions(
            name='cliente',
            options={'verbose_name_plural': 'Clientes'},
        ),
        migrations.AlterModelOptions(
            name='instructor',
            options={'verbose_name_plural': 'Instructores'},
        ),
    ]
