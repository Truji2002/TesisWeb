from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

from django.core.exceptions import ValidationError
import random
import string
import secrets
from django.db import transaction
from django.core.files.base import File
from reportlab.pdfgen import canvas
import io


class Empresa(models.Model):
    nombre = models.CharField(max_length=100,unique=True)
    area = models.CharField(max_length=100)
    direccion = models.CharField(max_length=100)
    telefono = models.CharField(max_length=100)
    correoElectronico = models.EmailField(unique=True)
    numeroEmpleados = models.IntegerField()
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
    def __str__(self):
        return self.nombre

    def contar_instructores(self):
        return self.instructores.count()

class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('instructor', 'Instructor'),
        ('estudiante', 'Estudiante'),
    ]
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    email = models.EmailField(unique=True)  
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='estudiante')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name','password']
    

    # Cambia los related_name para evitar conflictos
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="usuario_set",
        related_query_name="usuario",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="usuario_set",
        related_query_name="usuario",
    )
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def clean(self):
        
        if Usuario.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError({'email': 'Este correo electrónico ya está en uso.'})

        super().clean()



class Administrador(Usuario):
    
    cargo = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"

    def __str__(self):
        return f"Administrador: {self.email}"

    def save(self, *args, **kwargs):
        self.is_staff = True
        self.is_superuser = True
        self.rol = 'admin'
        super().save(*args, **kwargs)

    def asignar_cursos_a_instructor(self, instructor_id, cursos_ids):
        """
        Método para que el administrador asigne cursos a un instructor.
        
        Parámetros:
        - instructor_id: ID del instructor al que se asignarán los cursos.
        - cursos_ids: Lista de IDs de los cursos que se asignarán.
        
        Excepciones:
        - ValidationError si el instructor no existe o si alguno de los cursos no existe.
        """
        from django.db import transaction
        from django.core.exceptions import ValidationError
        from .models import Instructor, Curso, InstructorCurso

        try:
            # Obtener el instructor
            instructor = Instructor.objects.get(id=instructor_id)

            # Validar que los cursos existen
            cursos = Curso.objects.filter(id__in=cursos_ids)
            if len(cursos) != len(cursos_ids):
                raise ValidationError("Uno o más cursos no existen.")

            # Crear las asignaciones
            with transaction.atomic():
                for curso in cursos:
                    # Verificar si ya está asignado
                    if InstructorCurso.objects.filter(instructor=instructor, curso=curso).exists():
                        continue  # Saltar si ya está asignado

                    # Crear la relación
                    InstructorCurso.objects.create(
                        instructor=instructor,
                        curso=curso
                    )

            return f"Se asignaron {len(cursos)} cursos al instructor {instructor.email}."

        except Instructor.DoesNotExist:
            raise ValidationError("El instructor no existe.")
        except Exception as e:
            raise ValidationError(f"Ocurrió un error durante la asignación: {str(e)}")


class Instructor(Usuario):
    area = models.CharField(max_length=100)
    codigoOrganizacion = models.CharField(max_length=100, blank=False)
    fechaInicioCapacitacion = models.DateField()
    fechaFinCapacitacion = models.DateField()
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='instructores')
    debeCambiarContraseña = models.BooleanField(default=True)  

    class Meta:
        verbose_name = "Instructor"
        verbose_name_plural = "Instructores"

    def __str__(self):
        return f"Instructor: {self.email} - Área: {self.area} - Empresa: {self.empresa.nombre}"

    def save(self, *args, **kwargs):
        self.rol = 'instructor'
        if not self.codigoOrganizacion:
            prefix = self.empresa.nombre[:3].upper()
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.codigoOrganizacion = f"{prefix}-{suffix}"
            
        super().save(*args, **kwargs)

    def clean(self):
        if self.fechaInicioCapacitacion > self.fechaFinCapacitacion:
            raise ValidationError("La fecha de inicio de la capacitación no puede ser posterior a la fecha de fin.")
        super().clean()



    def generar_contraseña_temporal(self):
        temp_password = secrets.token_urlsafe(10)
        self.set_password(temp_password)
        self.save()
        return temp_password

# Clase Curso
class Curso(models.Model):
    titulo = models.CharField(max_length=200, null=True)
    descripcion = models.TextField(null=True)
    cantidadSubcursos = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to='documents/', null=True)
    simulacion = models.BooleanField(null=True)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

    def __str__(self):
        return self.titulo


class InstructorCurso(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='cursos_asignados')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='instructores_asignados')
    fecha_asignacion = models.DateField(auto_now_add=True)  # Fecha en la que se asigna el curso

    class Meta:
        verbose_name = "Instructor-Curso"
        verbose_name_plural = "Instructor-Cursos"
        unique_together = ('instructor', 'curso')  # Evita duplicados

    def __str__(self):
        return f"{self.instructor.email} - {self.curso.titulo} (Asignado el {self.fecha_asignacion})"

# Clase Subcurso
class Subcurso(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='subcursos')
    nombre = models.CharField(max_length=200)
    cantidad_modulos = models.IntegerField(default=0)


    class Meta:
        verbose_name = "Subcurso"
        verbose_name_plural = "Subcursos"

    def __str__(self):
        return f"{self.nombre} ({self.curso.titulo})"




# Clase Modulo
class Modulo(models.Model):
    subcurso = models.ForeignKey(Subcurso, on_delete=models.CASCADE, related_name='modulos', null=True)
    nombre = models.CharField(max_length=100)
    enlace = models.URLField(max_length=500, blank=True, null=True, help_text="Enlace al contenido del módulo")
    archivo = models.FileField(upload_to='documents/', null=True)


    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"

    def __str__(self):
        return f"{self.nombre}"





# Clase Prueba
class Prueba(models.Model):
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name='prueba', null=True)
    duracion = models.IntegerField()
    fechaCreacion = models.DateField()

    class Meta:
        verbose_name = "Prueba"
        verbose_name_plural = "Pruebas"




# Clase Progreso (tabla intermedia entre Curso y Estudiante)
class Progreso(models.Model):
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name='progresos')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='progresos')
    simulacionCompletada = models.BooleanField(null=True)
    contenidoCompletado = models.BooleanField(null=True)
    completado = models.BooleanField(default=False)
    porcentajeCompletado = models.FloatField(default=0)
    fechaInicioCurso=models.DateField(auto_now_add=True,null=True)
    fechaFinCurso=models.DateField(null=True)
    _skip_post_save = False

    class Meta:
        verbose_name = "Progreso"
        verbose_name_plural = "Progresos"

    def __str__(self):
        return f"{self.estudiante.email} - {self.curso.titulo}: {self.porcentajeCompletado}% completado"
    
    def calcular_porcentaje_completado(self):
        """
        Calcula el porcentaje completado del curso basado en las condiciones definidas.
        """
        
        # Obtener datos necesarios
        prueba = EstudiantePrueba.objects.filter(estudiante=self.estudiante, prueba__curso=self.curso).first()
        esta_aprobado = prueba.estaAprobado if prueba else False

        if self.curso.simulacion:
            # Regla de 3: simulación, contenido, prueba
            completado_total = sum([
                self.simulacionCompletada,
                self.contenidoCompletado,
                esta_aprobado
            ])
            self.porcentajeCompletado = (completado_total / 3) * 100
        else:
            # Regla de 2: contenido, prueba
            completado_total = sum([
                self.contenidoCompletado,
                esta_aprobado
            ])
            self.porcentajeCompletado = (completado_total / 2) * 100

        # Actualizar campo `completado`
        self.completado = self.porcentajeCompletado == 100

        self._skip_post_save = True  # Evita disparar la señal
        self.save()
        self._skip_post_save = False



class Estudiante(Usuario):
    
    codigoOrganizacion = models.CharField(max_length=100, blank=False)

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"

    def __str__(self):
        
        return f"Estudiante: {self.email}"

    def save(self, *args, **kwargs):
        self.rol = 'estudiante'
        # Validar que el código de organización sea válido
        if not Instructor.objects.filter(codigoOrganizacion=self.codigoOrganizacion,is_active=True).exists():
            raise ValidationError("El código de organización ingresado no corresponde a un instructor válido.")
        super().save(*args, **kwargs)

    @classmethod
    def crear_estudiante_con_cursos(cls, email, password, codigoOrganizacion, **kwargs):
        """
        Crea un estudiante y lo inscribe automáticamente en los cursos de su instructor.
        """
        try:
            # Verificar que el código de organización es válido
            instructor = Instructor.objects.get(codigoOrganizacion=codigoOrganizacion)

            # Crear el estudiante
            with transaction.atomic():
                estudiante = cls.objects.create(
                    email=email,
                    codigoOrganizacion=codigoOrganizacion,
                    **kwargs
                )
                estudiante.set_password(password)  # Configurar contraseña segura
                estudiante.save()

                # Inscribir al estudiante en los cursos del instructor
                cursos = Curso.objects.filter(
                    instructores_asignados__instructor__codigoOrganizacion=codigoOrganizacion
                )
                Progreso.objects.bulk_create([
                    Progreso(estudiante=estudiante, curso=curso, completado=False, porcentajeCompletado=0,simulacionCompletada=False)
                    for curso in cursos
                ])

            return estudiante

        except Instructor.DoesNotExist:
            raise ValidationError("El código de organización ingresado no corresponde a un instructor válido.")
        except Exception as e:
            raise ValidationError(f"Ocurrió un error al crear el estudiante: {str(e)}")

class EstudiantePrueba(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="progresos_prueba")
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name="progresos")
    estaAprobado = models.BooleanField(default=False)
    calificacion = models.FloatField(default=0.0)
    intento=models.IntegerField(default=0)
    fechaPrueba=models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'prueba')

class Certificado(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="certificados",null=True)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="certificados")
    fechaEmision = models.DateField(auto_now_add=True)
    archivoPdf = models.FileField(upload_to='certificados/', null=True, blank=True)  # Opcional, para guardar el archivo PDF del certificado

    class Meta:
        unique_together = ('estudiante', 'curso')  # Un estudiante no puede tener más de un certificado por curso.

    def __str__(self):
        return f"Certificado de {self.estudiante.email} para {self.curso.titulo}"

    @classmethod
    def emitir_certificado(cls, estudiante, curso):
        """
        Genera un certificado si el estudiante ha completado el curso.
        """
        try:
            # Verificar si el estudiante ya completó el curso
            progreso = Progreso.objects.filter(estudiante=estudiante, curso=curso, completado=True).first()
            if not progreso:
                return "El estudiante no ha completado el curso."

            # Verificar si ya existe un certificado para este estudiante y curso
            if cls.objects.filter(estudiante=estudiante, curso=curso).exists():
                return "El certificado ya ha sido emitido."

            # Validar datos
            if not estudiante.first_name or not estudiante.last_name:
                return "Los datos del estudiante son incompletos."
            if not curso.titulo:
                return "El título del curso no está disponible."

            # Generar el archivo PDF del certificado
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer)
            pdf.drawString(100, 750, "Certificado de Finalización")
            pdf.drawString(100, 730, f"Otorgado a: {estudiante.first_name} {estudiante.last_name}")
            pdf.drawString(100, 710, f"Por completar satisfactoriamente el curso: {curso.titulo}")
            pdf.save()
            buffer.seek(0)

            # Crear el certificado
            with transaction.atomic():
                certificado = cls.objects.create(estudiante=estudiante, curso=curso)
                certificado.archivoPdf.save(f"certificado_{curso.id}_{estudiante.id}.pdf", File(buffer))

            return "Certificado emitido exitosamente."

        except Exception as e:
            return f"Error al emitir el certificado: {str(e)}"


class Pregunta(models.Model):
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='preguntas')
    pregunta = models.TextField()
    opcionesRespuestas = models.TextField()  # Considerar usar un campo JSON si necesitas más estructura
    respuestaCorrecta = models.CharField(max_length=255)
    puntajePregunta = models.IntegerField()

    class Meta:
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"

    def __str__(self):
        return f"Pregunta: {self.pregunta[:50]}..."  # Mostrar solo los primeros 50 caracteres


