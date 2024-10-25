from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Administrador, Instructor, Cliente, Notificacion, Simulacion
from .models import Curso, Progreso, Certificado, Modulo,Prueba, Pregunta, Subcurso



#Admin para Administrador, Instructor y Cliente
admin.site.register(Usuario)
admin.site.register(Administrador)
admin.site.register(Instructor)
admin.site.register(Cliente)
admin.site.register(Notificacion)
admin.site.register(Simulacion)
admin.site.register(Curso)
admin.site.register(Progreso)
admin.site.register(Certificado)
admin.site.register(Modulo)
admin.site.register(Prueba)
admin.site.register(Pregunta)
admin.site.register(Subcurso)


