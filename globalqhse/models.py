from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import random
import string
from django.contrib.auth.hashers import make_password
import secrets






class Usuario(AbstractUser):
     
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    email = models.EmailField(unique=True)  
    empresa = models.CharField(max_length=100)
    codigoOrganizacion = models.CharField(max_length=100, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name','password','empresa','codigoOrganizacion']
    
    

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
    
    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"
    def __str__(self):
        return f"Administrador: {self.email}"
    def save(self, *args, **kwargs):
        if not self.codigoOrganizacion:
            
            prefix = self.empresa[:3].upper()  
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)) 
            self.codigoOrganizacion = f"{prefix}-{suffix}"
            self.is_staff=True
            self.is_superuser=True
        super().save(*args, **kwargs)


class Instructor(Usuario):
    area = models.CharField(max_length=100)
    fechaInicioContrato = models.DateField()
    fechaFinContrato = models.DateField()

    def asignar_simulacion_a_cliente(self, simulacion, cliente):
        if cliente.empresa != self.empresa:
            raise ValidationError("El cliente debe pertenecer a la misma empresa que el instructor.")
        if not simulacion.clientes.filter(id=cliente.id).exists():
            simulacion.clientes.add(cliente)
            simulacion.save()

    def save(self, *args, **kwargs):
        if not self.codigoOrganizacion:
            
            prefix = self.empresa[:3].upper()  
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5)) 
            self.codigoOrganizacion = f"{prefix}-{suffix}"
            if not self.is_active:
                Cliente.objects.filter(codigoOrganizacion=self.codigoOrganizacion).update(is_active=False)
        super().save(*args, **kwargs)

    def generar_contraseña_temporal(self):
        temp_password = secrets.token_urlsafe(10)  
        self.set_password(temp_password)  
        self.save()  
        return temp_password   
    
   
    
    class Meta:
        verbose_name = "Instructor"
        verbose_name_plural = "Instructores"

    def __str__(self):
        return f"Instructor: {self.email} - Área: {self.area}"
    
    def clean(self):
        if self.fechaInicioContrato > self.fechaFinContrato:
            raise ValidationError("La fecha de inicio del contrato no puede ser posterior a la fecha de fin del contrato.")
        super().clean()

class Cliente(Usuario):
    asignadoSimulacion = models.BooleanField(default=False)
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        estado_simulacion = "Con simulación" if self.asignadoSimulacion else "Sin simulación"
        return f"Cliente: {self.email} - {estado_simulacion}"

class Notificacion(models.Model):
    mensaje = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50)
    fechaEnvio = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.tipo} - {self.fechaEnvio.strftime('%Y-%m-%d %H:%M')}"
    

class Simulacion(models.Model):
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='simulacion',null=True)
    completado = models.BooleanField(default=False)
    fecha = models.DateField()



    class Meta:
        verbose_name = "Simulación"
        verbose_name_plural = "Simulaciones"

    def __str__(self):
        return f"Simulación programada para {self.fecha} - {'Activa' if self.estado else 'Inactiva'}"
    
class Curso(models.Model):
    titulo = models.CharField(max_length=200, null=True)
    descripcion = models.TextField(null=True)
    imagen=models.ImageField(upload_to='documents/', null=True)

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

class Subcurso(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='subcursos')
    nombre = models.CharField(max_length=200)
    cantidad_modulos = models.IntegerField(default=0)
    progreso = models.FloatField(default=0)

    def __str__(self):
        return f"{self.nombre} ({self.curso.titulo})"
    
    def actualizar_progreso(self):
        """Actualiza el progreso en porcentaje basado en módulos completados."""
        total_modulos = self.modulos.count()
        modulos_completados = self.modulos.filter(completado=True).count()
        if total_modulos > 0:
            self.progreso = (modulos_completados / total_modulos) * 100
        else:
            self.progreso = 0
        self.save()

    class Meta:
        verbose_name = "Subcurso"
        verbose_name_plural = "Subcursos"

class Progreso(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    completado = models.BooleanField(default=False)
    porcentajeCompletado = models.FloatField()

    class Meta:
        verbose_name = "Progreso"
        verbose_name_plural = "Progreso"

    def __str__(self):
        return f"{self.cliente} - {self.curso.titulo}: {self.porcentajeCompletado}% completado"

class Certificado(models.Model):
    codigoCertificado = models.CharField(max_length=100)
    estado = models.BooleanField(default=False)
    fechaEmision = models.DateField(auto_now_add=True)
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificados')
    simulacion = models.ForeignKey('Simulacion', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificados')

    def __str__(self):
        return f"Certificado {self.codigoCertificado} - {'Emitido' if self.estado else 'Pendiente'}"

    def verificar_emision(self):
        if self.curso and self.curso_progreso_completado():
            self.estado = True
            self.save()
        elif self.simulacion and self.simulacion.estado:
            self.estado = True
            self.save()

    def curso_progreso_completado(self):
        progreso = Progreso.objects.filter(curso=self.curso).first()
        return progreso and progreso.completado

    class Meta:
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"

class Modulo(models.Model):
    subcurso = models.ForeignKey(Subcurso, on_delete=models.CASCADE, related_name='modulos', null=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    enlace = models.URLField(max_length=500, blank=True, null=True, help_text="Enlace al contenido del módulo")
    archivo = models.FileField(upload_to='documents/', null=True)
    completado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"

    def __str__(self):
        return f"{self.nombre}"
    
# @receiver(post_save, sender=Modulo)
# def modulo_guardado(sender, instance, **kwargs):
#     if instance.pk:  # Si el módulo ya existe
#         instance.subcurso.actualizar_progreso()


    

class Prueba(models.Model):
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name='prueba',null=True)
    duracion = models.IntegerField()
    estaAprobado = models.BooleanField(default=False)
    calificacion = models.FloatField()
    fechaEvaluacion = models.DateField()
    def __str__(self):
        return f"Prueba Única - {'Aprobada' if self.estaAprobado else 'No Aprobada'}"
    
    class Meta:
        verbose_name = "Prueba"
        verbose_name_plural = "Prueba"




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


@receiver(post_save, sender=Modulo)
def actualizar_cantidad_modulos_y_progreso(sender, instance, created, **kwargs):
    subcurso = instance.subcurso
    if created:
        # Incrementar la cantidad de módulos cuando se crea un nuevo módulo
        subcurso.cantidad_modulos += 1
        subcurso.save()
    # Actualizar el progreso en el subcurso
    subcurso.actualizar_progreso()

@receiver(post_delete, sender=Modulo)
def disminuir_cantidad_modulos(sender, instance, **kwargs):
    try:
        subcurso = instance.subcurso
        # Verifica si el subcurso aún existe antes de intentar modificarlo
        if subcurso.cantidad_modulos > 0:
            subcurso.cantidad_modulos -= 1
            subcurso.save()
        # Actualizar el progreso en el subcurso
        subcurso.actualizar_progreso()
    except Subcurso.DoesNotExist:
        # El subcurso ya fue eliminado, así que no se hace nada
        pass