from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    codigoOrganizacion = models.CharField(max_length=100)
    empresa = models.CharField(max_length=100)
    

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


class Administrador(Usuario):
    
    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"


class Instructor(Usuario):
    area = models.CharField(max_length=100)
    fechaInicioContrato = models.DateField()
    fechaFinContrato = models.DateField()
    #esto es un metodo: asignarSimulacion = models.BooleanField(default=False)
    class Meta:
        verbose_name = "Instructor"
        verbose_name_plural = "Instructores"
    

class Cliente(Usuario):
    asignadoSimulacion = models.BooleanField(default=False)
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"