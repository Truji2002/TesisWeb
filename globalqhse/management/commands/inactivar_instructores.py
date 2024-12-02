from django.core.management.base import BaseCommand
from datetime import date
from globalqhse.models import Instructor

class Command(BaseCommand):
    help = 'Inactiva a los instructores cuya fecha fin de capacitación ha culminado.'

    def handle(self, *args, **kwargs):
        hoy = date.today()
        instructores_a_inactivar = Instructor.objects.filter(
            fechaFinCapacitacion__lt=hoy,
            is_active=True  # Solo inactiva instructores activos
        )

        for instructor in instructores_a_inactivar:
            instructor.is_active = False
            instructor.save()
            self.stdout.write(f"Instructor {instructor.email} inactivado.")

        self.stdout.write(f"Proceso completado. Total instructores inactivados: {instructores_a_inactivar.count()}")
