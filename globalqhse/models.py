from datetime import datetime							 
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models import Q
import qrcode
from reportlab.lib.pagesizes import letter,landscape
from rest_framework.response import Response
from rest_framework import status
import pytz
from reportlab.platypus import Paragraph, Frame, Spacer
from django.core.exceptions import ValidationError
import random
import string
import secrets
from django.db import transaction
from django.core.files.base import File
from reportlab.pdfgen import canvas
import os
from reportlab.lib.utils import ImageReader
import io
from django.utils import timezone
from django.utils.timezone import now
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
logger = logging.getLogger(__name__)


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

class Instructor(Usuario):
    
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='instructores')
    debeCambiarContraseña = models.BooleanField(default=True)  

    class Meta:
        verbose_name = "Instructor"
        verbose_name_plural = "Instructores"

    def __str__(self):
        return f"Instructor: {self.email} - Empresa: {self.empresa.nombre}"

    def save(self, *args, **kwargs):

        self.rol = 'instructor'
		
        super().save(*args, **kwargs)

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



class Contrato(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='cursos_asignados')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='instructores_asignados')
    codigoOrganizacion = models.CharField(max_length=100, blank=False)
    fechaInicioCapacitacion = models.DateField()
    fechaFinCapacitacion = models.DateField()
    activo = models.BooleanField(default=True)
 
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        constraints = [
        models.UniqueConstraint(
            fields=['instructor', 'curso', 'activo'],
            name='unique_instructor_curso_activo',
            condition=Q(activo=True)  
        )
    ]
 
    def __str__(self):
        return f"{self.instructor.email} - {self.curso.titulo}"
   
   
    def save(self, *args, **kwargs):
            
            if hasattr(self, '_force_codigo') and self._force_codigo:
                self.codigoOrganizacion = self._force_codigo
            elif not self.codigoOrganizacion:  
                prefix = self.instructor.empresa.nombre[:3].upper()
                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                self.codigoOrganizacion = f"{prefix}-{suffix}"
 
            super().save(*args, **kwargs)
 
    def set_force_codigo(self, codigo):
            """
            Método para establecer un código forzado antes de guardar.
            """
            self._force_codigo = codigo
 
    @classmethod
    def obtener_contratos_activos(cls):
        return cls.objects.filter(fechaFinCapacitacion__gte=datetime.date.today())
       
 
    def clean(self):
        if self.fechaInicioCapacitacion > self.fechaFinCapacitacion:
            raise ValidationError("La fecha de inicio de la capacitación no puede ser posterior a la fecha de fin.")
        super().clean()


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
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name='prueba')
    duracion = models.IntegerField()
    fechaCreacion = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Prueba"
        verbose_name_plural = "Pruebas"

    def __str__(self):
        return f"Prueba para el Curso: {self.curso.nombre}"

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
        unique_together = ('estudiante', 'curso')
   
        

    def __str__(self):
        return f"{self.estudiante.email} - {self.curso.titulo}: {self.porcentajeCompletado}% completado"
    
    def calcular_porcentaje_completado(self):
        """
        Calcula el porcentaje completado del curso basado en el progreso de subcursos, módulos, simulaciones y pruebas.
								   
        """
        
        subcursos = Subcurso.objects.filter(curso=self.curso)
        total_subcursos = subcursos.count() or 1  

       
        avance_total_subcursos = 0
        for subcurso in subcursos:
            estudiante_subcurso = EstudianteSubcurso.objects.filter(
                estudiante=self.estudiante, subcurso=subcurso
            ).first()
            if estudiante_subcurso:
                avance_total_subcursos += estudiante_subcurso.porcentajeCompletado

        
        porcentaje_contenido = avance_total_subcursos / total_subcursos

        
        simulacion_completada = self.simulacionCompletada or False
        prueba = EstudiantePrueba.objects.filter(estudiante=self.estudiante, prueba__curso=self.curso).first()
        esta_aprobado = prueba.estaAprobado if prueba else False

        
        if self.curso.simulacion:
           
            peso_contenido = 0.5
            peso_simulacion = 0.3
            peso_prueba = 0.2

            porcentaje_simulacion = 100 if simulacion_completada else 0
            porcentaje_prueba = 100 if esta_aprobado else 0

            self.porcentajeCompletado = (
                (porcentaje_contenido * peso_contenido) +
                (porcentaje_simulacion * peso_simulacion) +
                (porcentaje_prueba * peso_prueba)
            )
        else:
            
            peso_contenido = 0.8
            peso_prueba = 0.2

            porcentaje_prueba = 100 if esta_aprobado else 0

            self.porcentajeCompletado = (
                (porcentaje_contenido * peso_contenido) +
                (porcentaje_prueba * peso_prueba)
            )

        
        self.porcentajeCompletado = round(self.porcentajeCompletado, 2)
        if self.porcentajeCompletado >= 99:
            self.porcentajeCompletado = 100

        
        self.contenidoCompletado = porcentaje_contenido == 100
        self.completado = self.porcentajeCompletado == 100

       
        self._skip_post_save = True
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
        
        if not Contrato.objects.filter(codigoOrganizacion=self.codigoOrganizacion).exists():
            raise ValidationError("El código de organización ingresado no corresponde a un instructor válido.")
        super().save(*args, **kwargs)
 
    @classmethod
    def crear_estudiante_con_cursos(cls, email, password, codigoOrganizacion, **kwargs):
        """
        Crea un estudiante, lo inscribe automáticamente en los cursos de su instructor,
        y registra las pruebas asociadas en la tabla EstudiantePrueba.
        También crea registros en las tablas EstudianteSubcurso y EstudianteModulo.
        """
        try:
            
            contratos = Contrato.objects.filter(codigoOrganizacion=codigoOrganizacion)
            if not contratos.exists():
                raise ValidationError("El código de organización ingresado no corresponde a ningún contrato válido.")
 
            
            with transaction.atomic():
                estudiante = cls.objects.create(
                    email=email,
                    codigoOrganizacion=codigoOrganizacion,
                    **kwargs
                )
                estudiante.set_password(password)  
                estudiante.save()
 
                
                cursos_ids = contratos.values_list('curso_id', flat=True)
                cursos = Curso.objects.filter(id__in=cursos_ids)
                progreso_records = []
                estudiante_prueba_records = []
                estudiante_subcurso_records = []
                estudiante_modulo_records = []
 
                for curso in cursos:
                    
                    progreso_records.append(
                        Progreso(
                            estudiante=estudiante,
                            curso=curso,
                            completado=False,
                            porcentajeCompletado=0,
                            simulacionCompletada=False
                        )
                    )
 
                    
                    pruebas = Prueba.objects.filter(curso=curso)
                    for prueba in pruebas:
                        estudiante_prueba_records.append(
                            EstudiantePrueba(estudiante=estudiante, prueba=prueba)
                        )
 
                    
                    subcursos = Subcurso.objects.filter(curso=curso)
                    for subcurso in subcursos:
                        estudiante_subcurso_records.append(
                            EstudianteSubcurso(estudiante=estudiante, subcurso=subcurso, completado=False, porcentajeCompletado=0.0)
                        )
 
                        
                        modulos = Modulo.objects.filter(subcurso=subcurso)
                        for modulo in modulos:
                            estudiante_modulo_records.append(
                                EstudianteModulo(estudiante=estudiante, modulo=modulo, completado=False)
                            )
 
                
                Progreso.objects.bulk_create(progreso_records)
                EstudiantePrueba.objects.bulk_create(estudiante_prueba_records)
                EstudianteSubcurso.objects.bulk_create(estudiante_subcurso_records)
                EstudianteModulo.objects.bulk_create(estudiante_modulo_records)
 
            return estudiante
 
        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError(f"Ocurrió un error al crear el estudiante: {str(e)}")
        
class EstudiantePrueba(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="progresos_prueba")
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name="progresos")
    estaAprobado = models.BooleanField(default=False)
    calificacion = models.FloatField(default=0.0)
    intento = models.IntegerField(default=0)
    fechaPrueba = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'prueba')

    def calificar(self, respuestas_estudiante):
        logger.info(f"Calificando prueba {self.prueba.id} para estudiante {self.estudiante.id}")
        try:
            preguntas = self.prueba.preguntas.all()
            if not preguntas.exists():
                raise ValueError("No hay preguntas asociadas a la prueba.")

            respuestas_correctas = 0
            for pregunta in preguntas:
                if pregunta.respuestaCorrecta.lower() == respuestas_estudiante.get(str(pregunta.id), "").lower():
                    respuestas_correctas += 1

            self.calificacion = (respuestas_correctas / preguntas.count()) * 100
            self.estaAprobado = self.calificacion >= 60
            self.intento += 1

            
            self._skip_post_save = True
            self.save()
            self._skip_post_save = False
        except Exception as e:
            logger.error(f"Error al calificar: {e}")
            raise


    
class Certificado(models.Model):
    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.CASCADE, related_name="certificados", null=True
    )
    curso = models.ForeignKey(
        Curso, on_delete=models.CASCADE, related_name="certificados"
    )
    fechaEmision = models.DateField(auto_now_add=True)
    archivoPdf = models.FileField(upload_to="certificados/", null=True, blank=True)

    class Meta:
        unique_together = ("estudiante", "curso")

    def __str__(self):
        return f"Certificado de {self.estudiante.email} para {self.curso.titulo}"

    @classmethod
    def emitir_certificado(cls, estudiante, curso):
        try:
            # Verificamos que el estudiante haya completado el curso.
            progreso = Progreso.objects.filter(estudiante=estudiante, curso=curso, completado=True).first()
            if not progreso:
                return "El estudiante no ha completado el curso."

            # Verificamos si ya existe un certificado para este estudiante y curso.
            if cls.objects.filter(estudiante=estudiante, curso=curso).exists():
                return "El certificado ya ha sido emitido."

            # Validamos datos básicos.
            if not estudiante.first_name or not estudiante.last_name:
                return "Los datos del estudiante son incompletos."
            if not curso.titulo:
                return "El título del curso no está disponible."

            # Creamos el buffer para construir el PDF.
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
            width, height = landscape(letter)

        
            pdf.setFillColor(HexColor("#FFFFFF"))
            pdf.rect(0, 0, width, height, fill=1)

            pdf.setFillColor(HexColor("#2F4798"))  # Azul claro
            top_wave_1 = pdf.beginPath()
            top_wave_1.moveTo(0, height)
            top_wave_1.curveTo(width * 0.3, height - 100, width * 0.7, height - 50, width, height - 80)
            top_wave_1.lineTo(width, height)
            top_wave_1.lineTo(0, height)
            top_wave_1.close()
            pdf.drawPath(top_wave_1, fill=1, stroke=0)

            # Onda Superior (capa 2)
            pdf.setFillColor(HexColor("#1A2E6F"))  # Azul oscuro
            top_wave_2 = pdf.beginPath()
            top_wave_2.moveTo(0, height)
            top_wave_2.curveTo(width * 0.3, height - 50, width * 0.7, height - 80, width, height - 60)
            top_wave_2.lineTo(width, height)
            top_wave_2.lineTo(0, height)
            top_wave_2.close()
            pdf.drawPath(top_wave_2, fill=1, stroke=0)

          
            pdf.setFillColor(HexColor("#C9A66B"))  # Dorado
            pdf.setFont("Helvetica-Bold", 36)
            pdf.drawCentredString(width / 2, height - 180, "CERTIFICADO DE RECONOCIMIENTO")

            # Onda Inferior (capa 1)
            pdf.setFillColor(HexColor("#2F4798"))
            bottom_wave_1 = pdf.beginPath()
            bottom_wave_1.moveTo(0, 0)
            bottom_wave_1.curveTo(width * 0.3, 100, width * 0.7, 50, width, 80)
            bottom_wave_1.lineTo(width, 0)
            bottom_wave_1.lineTo(0, 0)
            bottom_wave_1.close()
            pdf.drawPath(bottom_wave_1, fill=1, stroke=0)

            # Onda Inferior (capa 2)
            pdf.setFillColor(HexColor("#1A2E6F"))
            bottom_wave_2 = pdf.beginPath()
            bottom_wave_2.moveTo(0, 0)
            bottom_wave_2.curveTo(width * 0.3, 50, width * 0.7, 80, width, 60)
            bottom_wave_2.lineTo(width, 0)
            bottom_wave_2.lineTo(0, 0)
            bottom_wave_2.close()
            pdf.drawPath(bottom_wave_2, fill=1, stroke=0)

           
            pdf.setFillColor(HexColor("#333333"))
            pdf.setFont("Helvetica", 16)
            pdf.drawCentredString(width / 2, height - 250, "Otorgado a")

            # Nombre del estudiante
            pdf.setFont("Helvetica-Bold", 28)
            pdf.setFillColor(HexColor("#4444AA"))
            pdf.drawCentredString(
                width / 2,
                height - 300,
                f"{estudiante.first_name} {estudiante.last_name}"
            )

            # Explicación
            pdf.setFont("Helvetica", 16)
            pdf.setFillColor(HexColor("#333333"))
            pdf.drawCentredString(
                width / 2,
                height - 350,
                "Por haber completado satisfactoriamente el siguiente curso:"
            )

      
            pdf.setFont("Helvetica-Bold", 20)
            pdf.setFillColor(HexColor("#C9A66B"))  
            pdf.drawCentredString(width / 2, height - 400, curso.titulo)

            fecha_actual_utc = now()

            
            zona_horaria_ecuador = pytz.timezone('America/Guayaquil')
            fecha_actual_ecuador = fecha_actual_utc.astimezone(zona_horaria_ecuador)

            pdf.setFont("Helvetica", 14)
            pdf.setFillColor(HexColor("#666666"))
            pdf.drawCentredString(
                width / 2,
                height - 450,
                f"Fecha de emisión: {fecha_actual_ecuador.strftime('%d de %B de %Y')}"
            )

         
            pdf.setFont("Helvetica-Bold", 14)
            pdf.setFillColor(HexColor("#333333"))
            pdf.drawCentredString(width / 2, height - 520, "Firma Autorizada - Global QHSE")

           
            pdf.save()
            buffer.seek(0)

          
            with transaction.atomic():
                certificado = cls.objects.create(estudiante=estudiante, curso=curso)
                certificado.archivoPdf.save(
                    f"certificado_{curso.id}_{estudiante.id}.pdf",
                    File(buffer)
                )

            return "Certificado emitido exitosamente."

        except Exception as e:
            return f"Error al emitir el certificado: {str(e)}"
 
    def post(self, request):
        estudiante_id = request.data.get('estudiante_id')
        curso_id = request.data.get('curso_id')
 
        if not estudiante_id or not curso_id:
            return Response(
                {"error": "Faltan los parámetros 'estudiante_id' y 'curso_id'."},
                status=status.HTTP_400_BAD_REQUEST
            )
 
        try:
            certificado = Certificado.objects.filter(estudiante_id=estudiante_id, curso_id=curso_id)
            if certificado.exists():
                certificado.delete()
                return Response({"message": "Certificado eliminado exitosamente."}, status=status.HTTP_200_OK)
            return Response({"error": "Certificado no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 

class Pregunta(models.Model):
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='preguntas')
    pregunta = models.TextField()
    opcionesRespuestas = models.JSONField()  
    respuestaCorrecta = models.CharField(max_length=255)
    puntajePregunta = models.IntegerField()

    class Meta:
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"

    def __str__(self):
        return f"Pregunta: {self.pregunta[:50]}..."
class EstudianteSubcurso(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="subcursos")
    subcurso = models.ForeignKey(Subcurso, on_delete=models.CASCADE, related_name="estudiantes")
    completado = models.BooleanField(default=False)
    porcentajeCompletado = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('estudiante', 'subcurso')
        verbose_name = "Estudiante-Subcurso"
        verbose_name_plural = "Estudiantes-Subcursos"

    def __str__(self):
        return f"{self.estudiante.email} - {self.subcurso.nombre}"
    
class EstudianteModulo(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name="modulos")
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name="estudiantes")
    completado = models.BooleanField(default=False)

    class Meta:
        unique_together = ('estudiante', 'modulo')
        verbose_name = "Estudiante-Modulo"
        verbose_name_plural = "Estudiantes-Modulos"

    def __str__(self):
        return f"{self.estudiante.email} - {self.modulo.nombre}"								   