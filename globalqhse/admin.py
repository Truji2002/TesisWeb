from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Administrador, Instructor, Cliente



#Admin para Administrador, Instructor y Cliente
admin.site.register(Administrador)
admin.site.register(Instructor)
admin.site.register(Cliente)


