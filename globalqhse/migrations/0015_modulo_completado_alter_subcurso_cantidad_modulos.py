# Generated by Django 4.2 on 2024-09-07 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('globalqhse', '0014_alter_curso_options_alter_subcurso_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='modulo',
            name='completado',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='subcurso',
            name='cantidad_modulos',
            field=models.IntegerField(default=0),
        ),
    ]
