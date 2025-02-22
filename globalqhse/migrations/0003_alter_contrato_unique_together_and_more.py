# Generated by Django 4.2 on 2025-01-11 18:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('globalqhse', '0002_alter_contrato_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='contrato',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='contrato',
            constraint=models.UniqueConstraint(condition=models.Q(('activo', True)), fields=('instructor', 'curso', 'activo'), name='unique_instructor_curso_activo'),
        ),
    ]
