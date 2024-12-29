from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Curso, Subcurso, Modulo,Progreso,Certificado,EstudiantePrueba

@receiver(post_save, sender=Modulo)
def actualizar_cantidad_modulos_y_progreso(sender, instance, created, **kwargs):
    subcurso = instance.subcurso
    if created:
        subcurso.cantidad_modulos += 1
        subcurso.save()
    subcurso.actualizar_progreso()


@receiver(post_delete, sender=Modulo)
def disminuir_cantidad_modulos(sender, instance, **kwargs):
    try:
        subcurso = instance.subcurso
        if subcurso.cantidad_modulos > 0:
            subcurso.cantidad_modulos -= 1
            subcurso.save()
        subcurso.actualizar_progreso()
    except Subcurso.DoesNotExist:
        pass

@receiver(post_save, sender=Subcurso)
def actualizar_cantidad_subcursos(sender, instance, created, **kwargs):
    """
    Actualiza la cantidad de subcursos en el curso cuando se crea un nuevo subcurso.
    """
    if created:
        curso = instance.curso
        curso.cantidadSubcursos = curso.subcursos.count()
        curso.save()

@receiver(post_delete, sender=Subcurso)
def disminuir_cantidad_subcursos(sender, instance, **kwargs):
    """
    Actualiza la cantidad de subcursos en el curso cuando se elimina un subcurso.
    """
    curso = instance.curso
    curso.cantidadSubcursos = curso.subcursos.count()
    curso.save()


@receiver(post_save, sender=Progreso)
def emitir_certificado_automatico(sender, instance, **kwargs):
    if instance.completado:  # Si el progreso está completo
        Certificado.emitir_certificado(estudiante=instance.estudiante, curso=instance.curso)


@receiver(post_save, sender=Progreso)
def actualizar_progreso_curso(sender, instance, **kwargs):
    """
    Actualiza el porcentaje completado del curso cada vez que se guarda un progreso.
    """
    if instance._skip_post_save:
        return
    
    instance.calcular_porcentaje_completado()

@receiver(post_save, sender=EstudiantePrueba)
def actualizar_progreso_con_prueba(sender, instance, **kwargs):
    """
    Actualiza el progreso del curso relacionado cada vez que se guarda un registro de prueba.
    """
    progreso = Progreso.objects.filter(estudiante=instance.estudiante, curso=instance.prueba.curso).first()
    if progreso:
        progreso.calcular_porcentaje_completado()