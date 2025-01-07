from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .utils.email import EmailService
from .models import Curso, Subcurso, Modulo,Progreso,Certificado,EstudiantePrueba,EstudianteSubcurso,EstudianteModulo,Contrato

@receiver(post_save, sender=Modulo)
def actualizar_cantidad_modulos_y_progreso(sender, instance, created, **kwargs):
    subcurso = instance.subcurso
    if created:
        subcurso.cantidad_modulos += 1
        subcurso.save()
    


@receiver(post_delete, sender=Modulo)
def disminuir_cantidad_modulos(sender, instance, **kwargs):
    try:
        subcurso = instance.subcurso
        if subcurso.cantidad_modulos > 0:
            subcurso.cantidad_modulos -= 1
            subcurso.save()
        
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
    if hasattr(instance, '_skip_post_save') and instance._skip_post_save:
        return
   
    # Actualizar el progreso
    instance._skip_post_save = True
    instance.calcular_porcentaje_completado()
    instance._skip_post_save = False
 
 
@receiver(post_save, sender=EstudiantePrueba)
def actualizar_progreso_con_prueba(sender, instance, **kwargs):
    """
    Actualiza el progreso del curso relacionado cada vez que se guarda un registro de prueba.
    """
    progreso = Progreso.objects.filter(estudiante=instance.estudiante, curso=instance.prueba.curso).first()
    if progreso:
        # Evitar el ciclo infinito
        if hasattr(progreso, '_skip_post_save') and progreso._skip_post_save:
            return
 
        progreso._skip_post_save = True
        progreso.calcular_porcentaje_completado()
        progreso._skip_post_save = False
 

@receiver(post_save, sender=EstudianteModulo)
def actualizar_progreso_con_modulo(sender, instance, **kwargs):
    """
    Actualiza el progreso del subcurso relacionado cada vez que se guarda un registro de EstudianteModulo.
    """
    subcurso = instance.modulo.subcurso
    estudiante = instance.estudiante

    # Obtener todos los módulos del subcurso
    modulos = Modulo.objects.filter(subcurso=subcurso)
    total_modulos = modulos.count()

    # Contar los módulos completados por el estudiante
    modulos_completados = EstudianteModulo.objects.filter(
        estudiante=estudiante, modulo__in=modulos, completado=True
    ).count()

    # Calcular el porcentaje completado del subcurso
    porcentaje_completado = (modulos_completados / total_modulos) * 100 if total_modulos > 0 else 0
    # Redondear a 2 decimales
    porcentaje_completado = round(porcentaje_completado, 2)
    # Si es mayor o igual a 99, establecer en 100
    porcentaje_completado = 100 if porcentaje_completado >= 99 else porcentaje_completado


    # Actualizar el registro de EstudianteSubcurso
    estudiante_subcurso, created = EstudianteSubcurso.objects.get_or_create(
        estudiante=estudiante, subcurso=subcurso
    )
    estudiante_subcurso.porcentajeCompletado = porcentaje_completado
    estudiante_subcurso.completado = porcentaje_completado == 100
    estudiante_subcurso.save()


@receiver(post_save, sender=EstudianteSubcurso)
def actualizar_progreso_con_subcurso(sender, instance, **kwargs):
    """
    Actualiza el progreso del curso relacionado cada vez que se guarda un registro de EstudianteSubcurso.
    """
    curso = instance.subcurso.curso
    estudiante = instance.estudiante

    # Obtener todos los subcursos del curso
    subcursos = Subcurso.objects.filter(curso=curso)
    total_subcursos = subcursos.count()

    if total_subcursos == 0:
        return  # Si no hay subcursos, no se hace nada

    # Contar los subcursos completados por el estudiante
    subcursos_completados = EstudianteSubcurso.objects.filter(
        estudiante=estudiante, subcurso__in=subcursos, completado=True
    ).count()

    # Calcular el porcentaje completado del curso (basado en subcursos)
    porcentaje_completado = (subcursos_completados / total_subcursos) * 100

    # Actualizar el registro de Progreso
    progreso, created = Progreso.objects.get_or_create(
        estudiante=estudiante, curso=curso
    )
    progreso.contenidoCompletado = porcentaje_completado == 100
    progreso.save()  # Guarda el estado actualizado del contenido completado

    # Recalcular el porcentaje general del curso
    progreso.calcular_porcentaje_completado()