from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Administrador, Instructor, Empresa,Estudiante
from .models import Curso, Progreso, Certificado, Modulo,Prueba, Pregunta, Subcurso



###Quitar el models de SImulación 


#Admin para Administrador, Instructor y Cliente
admin.site.register(Usuario)
admin.site.register(Administrador)
admin.site.register(Instructor)
admin.site.register(Estudiante)
admin.site.register(Empresa)

admin.site.register(Curso)
admin.site.register(Progreso)
admin.site.register(Certificado)
admin.site.register(Modulo)
admin.site.register(Prueba)
admin.site.register(Pregunta)
admin.site.register(Subcurso)


