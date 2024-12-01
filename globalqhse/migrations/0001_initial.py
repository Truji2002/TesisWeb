# Generated by Django 4.2 on 2024-11-27 02:57

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('username', models.CharField(blank=True, max_length=150, null=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('rol', models.CharField(choices=[('admin', 'Administrador'), ('instructor', 'Instructor'), ('estudiante', 'Estudiante')], default='estudiante', max_length=20)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='usuario_set', related_query_name='usuario', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='usuario_set', related_query_name='usuario', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'Usuario',
                'verbose_name_plural': 'Usuarios',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Curso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200, null=True)),
                ('descripcion', models.TextField(null=True)),
                ('cantidadSubcursos', models.IntegerField(default=0)),
                ('imagen', models.ImageField(null=True, upload_to='documents/')),
            ],
            options={
                'verbose_name': 'Curso',
                'verbose_name_plural': 'Cursos',
            },
        ),
        migrations.CreateModel(
            name='Empresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('area', models.CharField(max_length=100)),
                ('direccion', models.CharField(max_length=100)),
                ('telefono', models.CharField(max_length=100)),
                ('correoElectronico', models.CharField(max_length=100)),
                ('numeroEmpleados', models.IntegerField()),
            ],
            options={
                'verbose_name': 'Empresa',
                'verbose_name_plural': 'Empresas',
            },
        ),
        migrations.CreateModel(
            name='Administrador',
            fields=[
                ('usuario_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('cargo', models.CharField(blank=True, max_length=100)),
            ],
            options={
                'verbose_name': 'Administrador',
                'verbose_name_plural': 'Administradores',
            },
            bases=('globalqhse.usuario',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Estudiante',
            fields=[
                ('usuario_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('asignadoSimulacion', models.BooleanField(default=False)),
                ('codigoOrganizacion', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'Estudiante',
                'verbose_name_plural': 'Estudiantes',
            },
            bases=('globalqhse.usuario',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Instructor',
            fields=[
                ('usuario_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('area', models.CharField(max_length=100)),
                ('codigoOrganizacion', models.CharField(max_length=100, unique=True)),
                ('fechaInicioCapacitacion', models.DateField()),
                ('fechaFinCapacitacion', models.DateField()),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instructores', to='globalqhse.empresa')),
            ],
            options={
                'verbose_name': 'Instructor',
                'verbose_name_plural': 'Instructores',
            },
            bases=('globalqhse.usuario',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Subcurso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200)),
                ('cantidad_modulos', models.IntegerField(default=0)),
                ('progreso', models.FloatField(default=0)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subcursos', to='globalqhse.curso')),
            ],
            options={
                'verbose_name': 'Subcurso',
                'verbose_name_plural': 'Subcursos',
            },
        ),
        migrations.CreateModel(
            name='Simulacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.BooleanField(default=False)),
                ('fecha', models.DateField()),
                ('curso', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='simulacion', to='globalqhse.curso')),
            ],
            options={
                'verbose_name': 'Simulación',
                'verbose_name_plural': 'Simulaciones',
            },
        ),
        migrations.CreateModel(
            name='Prueba',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duracion', models.IntegerField()),
                ('estaAprobado', models.BooleanField(default=False)),
                ('calificacion', models.FloatField()),
                ('fechaEvaluacion', models.DateField()),
                ('curso', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='prueba', to='globalqhse.curso')),
            ],
            options={
                'verbose_name': 'Prueba',
                'verbose_name_plural': 'Pruebas',
            },
        ),
        migrations.CreateModel(
            name='Pregunta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pregunta', models.TextField()),
                ('opcionesRespuestas', models.TextField()),
                ('respuestaCorrecta', models.CharField(max_length=255)),
                ('puntajePregunta', models.IntegerField()),
                ('prueba', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preguntas', to='globalqhse.prueba')),
            ],
            options={
                'verbose_name': 'Pregunta',
                'verbose_name_plural': 'Preguntas',
            },
        ),
        migrations.CreateModel(
            name='Modulo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('enlace', models.URLField(blank=True, help_text='Enlace al contenido del módulo', max_length=500, null=True)),
                ('archivo', models.FileField(null=True, upload_to='documents/')),
                ('completado', models.BooleanField(default=False)),
                ('subcurso', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='modulos', to='globalqhse.subcurso')),
            ],
            options={
                'verbose_name': 'Módulo',
                'verbose_name_plural': 'Módulos',
            },
        ),
        migrations.CreateModel(
            name='Certificado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigoCertificado', models.CharField(max_length=100)),
                ('estado', models.BooleanField(default=False)),
                ('fechaEmision', models.DateField(auto_now_add=True)),
                ('curso', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='certificado', to='globalqhse.curso')),
            ],
            options={
                'verbose_name': 'Certificado',
                'verbose_name_plural': 'Certificados',
            },
        ),
        migrations.CreateModel(
            name='Progreso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completado', models.BooleanField(default=False)),
                ('porcentajeCompletado', models.FloatField(default=0)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progresos', to='globalqhse.curso')),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progresos', to='globalqhse.estudiante')),
            ],
            options={
                'verbose_name': 'Progreso',
                'verbose_name_plural': 'Progresos',
            },
        ),
        migrations.CreateModel(
            name='InstructorCurso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_asignacion', models.DateField(auto_now_add=True)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='instructores_asignados', to='globalqhse.curso')),
                ('instructor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cursos_asignados', to='globalqhse.instructor')),
            ],
            options={
                'verbose_name': 'Instructor-Curso',
                'verbose_name_plural': 'Instructor-Cursos',
                'unique_together': {('instructor', 'curso')},
            },
        ),
    ]
