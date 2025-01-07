from django.core.management.base import BaseCommand
from datetime import date
from globalqhse.models import Contrato

class Command(BaseCommand):
    help = 'Inactiva los contratos cuya fecha fin de capacitación ha culminado.'

    def handle(self, *args, **kwargs):
        hoy = date.today()

        # Filtrar contratos cuya fecha de fin de capacitación ya pasó y que están activos
        contratos_a_inactivar = Contrato.objects.filter(
            fechaFinCapacitacion__lt=hoy,
            activo=True  # Solo inactiva contratos activos
        )

        for contrato in contratos_a_inactivar:
            contrato.activo = False
            contrato.save()
            self.stdout.write(f"Contrato con código de organización {contrato.codigoOrganizacion} y curso {contrato.curso.titulo} inactivado.")

        self.stdout.write(f"Proceso completado. Total contratos inactivados: {contratos_a_inactivar.count()}")