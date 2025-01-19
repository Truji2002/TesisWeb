from django.test import TestCase
from rest_framework.test import APITestCase
from datetime import date
from globalqhse.models import (
    Empresa, Usuario, Administrador, Instructor, Estudiante,
    Curso, Subcurso, Modulo, Prueba, Progreso, Contrato,
    Certificado, Pregunta, EstudianteSubcurso, EstudianteModulo, EstudiantePrueba
)

from globalqhse.serializers import (
    EmpresaSerializer, AdministradorSerializer, InstructorSerializer, EstudianteSerializer,
    CursoSerializer, SubcursoSerializer, ModuloSerializer, ContratoSerializer, ProgresoSerializer,
    PreguntaSerializer, PruebaSerializer
)
from django.core.exceptions import ValidationError
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

#models
class EmpresaModelTests(TestCase):

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa 1",
            area="Educación",
            direccion="Calle Falsa 123",
            telefono="123456789",
            correoElectronico="empresa1@example.com",
            numeroEmpleados=50
        )

    def test_empresa_creation(self):
        self.assertEqual(Empresa.objects.count(), 1)
        self.assertEqual(self.empresa.nombre, "Empresa 1")

    def test_contar_instructores(self):
        self.assertEqual(self.empresa.contar_instructores(), 0)


class UsuarioModelTests(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create(
            email="usuario@example.com",
            password="securepassword",
            first_name="John",
            last_name="Doe"
        )
        self.usuario.set_password("securepassword")
        self.usuario.save()

    def test_usuario_creation(self):
        self.assertEqual(Usuario.objects.count(), 1)
        self.assertEqual(self.usuario.email, "usuario@example.com")

    def test_unique_email_validation(self):
        usuario_duplicado = Usuario(
            email="usuario@example.com",
            password="anotherpassword",
            first_name="Jane",
            last_name="Doe"
        )
        with self.assertRaises(ValidationError):
            usuario_duplicado.full_clean()


class AdministradorModelTests(TestCase):

    def setUp(self):
        self.admin = Administrador.objects.create(
            email="admin@example.com",
            password="adminpassword",
            first_name="Admin",
            last_name="User"
        )
        self.admin.set_password("adminpassword")
        self.admin.save()

    def test_administrador_creation(self):
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_superuser)
        self.assertEqual(self.admin.rol, "admin")


class InstructorModelTests(TestCase):

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa 2",
            area="Tecnología",
            direccion="Avenida Siempre Viva 456",
            telefono="987654321",
            correoElectronico="empresa2@example.com",
            numeroEmpleados=100
        )
        self.instructor = Instructor.objects.create(
            email="instructor@example.com",
            password="instructorpassword",
            first_name="Instructor",
            last_name="One",
            empresa=self.empresa
        )
        self.instructor.set_password("instructorpassword")
        self.instructor.save()

    def test_instructor_creation(self):
        self.assertEqual(Instructor.objects.count(), 1)
        self.assertEqual(self.instructor.empresa, self.empresa)
        self.assertEqual(self.instructor.rol, "instructor")


class CursoModelTests(TestCase):

    def setUp(self):
        self.curso = Curso.objects.create(
            titulo="Curso de Django",
            descripcion="Curso introductorio sobre Django",
            simulacion=True
        )

    def test_curso_creation(self):
        self.assertEqual(Curso.objects.count(), 1)
        self.assertEqual(self.curso.titulo, "Curso de Django")


class SubcursoModelTests(TestCase):

    def setUp(self):
        self.curso = Curso.objects.create(
            titulo="Curso de Python",
            descripcion="Curso avanzado de Python"
        )
        self.subcurso = Subcurso.objects.create(
            curso=self.curso,
            nombre="Subcurso Avanzado"
        )

    def test_subcurso_creation(self):
        self.assertEqual(Subcurso.objects.count(), 1)
        self.assertEqual(self.subcurso.nombre, "Subcurso Avanzado")


class ModuloModelTests(TestCase):

    def setUp(self):
        self.curso = Curso.objects.create(
            titulo="Curso de AI",
            descripcion="Curso introductorio de inteligencia artificial"
        )
        self.subcurso = Subcurso.objects.create(
            curso=self.curso,
            nombre="Subcurso de Redes Neuronales"
        )
        self.modulo = Modulo.objects.create(
            subcurso=self.subcurso,
            nombre="Introducción a Redes Neuronales"
        )

    def test_modulo_creation(self):
        self.assertEqual(Modulo.objects.count(), 1)
        self.assertEqual(self.modulo.nombre, "Introducción a Redes Neuronales")


class ContratoModelTests(TestCase):

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa 3",
            area="Salud",
            direccion="Calle Salud 789",
            telefono="123123123",
            correoElectronico="empresa3@example.com",
            numeroEmpleados=200
        )
        self.instructor = Instructor.objects.create(
            email="instructor2@example.com",
            password="instructorpassword",
            empresa=self.empresa
        )
        self.instructor.set_password("instructorpassword")
        self.instructor.save()
        self.curso = Curso.objects.create(
            titulo="Curso de Seguridad Ocupacional",
            descripcion="Capacitación para seguridad en el trabajo"
        )
        self.contrato = Contrato.objects.create(
            instructor=self.instructor,
            curso=self.curso,
            codigoOrganizacion="EMP-12345",
            fechaInicioCapacitacion=date(2024, 1, 1),
            fechaFinCapacitacion=date(2024, 12, 31)
        )

    def test_contrato_creation(self):
        self.assertEqual(Contrato.objects.count(), 1)
        self.assertEqual(self.contrato.codigoOrganizacion, "EMP-12345")

#Serializers
class EmpresaSerializerTests(TestCase):
    def test_empresa_serialization(self):
        empresa = Empresa.objects.create(
            nombre="Empresa Prueba",
            area="Tecnología",
            direccion="Calle Falsa 123",
            telefono="123456789",
            correoElectronico="empresa@example.com",
            numeroEmpleados=50
        )
        serializer = EmpresaSerializer(empresa)
        self.assertEqual(serializer.data["nombre"], "Empresa Prueba")

    def test_empresa_deserialization(self):
        data = {
            "nombre": "Empresa Test",
            "area": "Educación",
            "direccion": "Calle Real 456",
            "telefono": "987654321",
            "correoElectronico": "test@example.com",
            "numeroEmpleados": 20
        }
        serializer = EmpresaSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        empresa = serializer.save()
        self.assertEqual(empresa.nombre, "Empresa Test")


class AdministradorSerializerTests(TestCase):
    def test_administrador_creation(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "admin@example.com",
            "password": "Secure123!",
            "cargo": "Gerente"
        }
        serializer = AdministradorSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        admin = serializer.save()
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.check_password("Secure123!"))

    def test_password_validation(self):
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "admin2@example.com",
            "password": "short",
            "cargo": "Supervisor"
        }
        serializer = AdministradorSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)


class InstructorSerializerTests(TestCase):
    def test_instructor_creation_with_temp_password(self):
        empresa = Empresa.objects.create(
            nombre="Empresa Demo",
            area="Finanzas",
            direccion="Av. Siempre Viva 123",
            telefono="123456789",
            correoElectronico="empresa_demo@example.com",
            numeroEmpleados=100
        )
        data = {
            "first_name": "Carlos",
            "last_name": "Perez",
            "email": "instructor@example.com",
            "password": "Password123",
            "empresa": empresa.id
        }
        serializer = InstructorSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        instructor = serializer.save()
        self.assertEqual(instructor.empresa, empresa)


class EstudianteSerializerTests(TestCase):
    def test_estudiante_creation(self):
        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            area="Educación",
            direccion="Calle Real 456",
            telefono="987654321",
            correoElectronico="empresa_test@example.com",
            numeroEmpleados=100
        )
        contrato = Contrato.objects.create(
            instructor=Instructor.objects.create(
                first_name="Instructor",
                last_name="Uno",
                email="instructor@example.com",
                password="Password123",
                empresa=empresa
            ),
            curso=Curso.objects.create(titulo="Curso Test", descripcion="Descripción del curso"),
            codigoOrganizacion="ORG123",
            fechaInicioCapacitacion="2024-01-01",
            fechaFinCapacitacion="2024-12-31"
        )
        data = {
            "first_name": "Maria",
            "last_name": "Lopez",
            "email": "estudiante@example.com",
            "password": "Password123",
            "codigoOrganizacion": "ORG123"
        }
        serializer = EstudianteSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        estudiante = serializer.save()
        self.assertEqual(estudiante.email, "estudiante@example.com")

    def test_duplicate_email(self):
        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            area="Educación",
            direccion="Calle Real 456",
            telefono="987654321",
            correoElectronico="empresa_test@example.com",
            numeroEmpleados=100
        )
        contrato = Contrato.objects.create(
            instructor=Instructor.objects.create(
                first_name="Instructor",
                last_name="Uno",
                email="instructor@example.com",
                password="Password123",
                empresa=empresa
            ),
            curso=Curso.objects.create(titulo="Curso Test", descripcion="Descripción del curso"),
            codigoOrganizacion="ORG123",
            fechaInicioCapacitacion="2024-01-01",
            fechaFinCapacitacion="2024-12-31"
        )
        Estudiante.objects.create(
            first_name="Maria",
            last_name="Lopez",
            email="estudiante@example.com",
            password="Password123",
            codigoOrganizacion="ORG123"
        )
        data = {
            "first_name": "Carlos",
            "last_name": "Gomez",
            "email": "estudiante@example.com",
            "password": "Password123",
            "codigoOrganizacion": "ORG456"
        }
        serializer = EstudianteSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)


class CursoSerializerTests(TestCase):
    def test_curso_serialization(self):
        curso = Curso.objects.create(
            titulo="Curso de Django",
            descripcion="Curso para aprender Django",
            simulacion=True
        )
        serializer = CursoSerializer(curso)
        self.assertEqual(serializer.data["titulo"], "Curso de Django")

    def test_curso_prueba_relation(self):
        curso = Curso.objects.create(
            titulo="Curso de Python",
            descripcion="Curso avanzado de Python"
        )
        Prueba.objects.create(curso=curso, duracion=60)
        serializer = CursoSerializer(curso)
        self.assertTrue(serializer.data["has_prueba"])


class ModuloSerializerTests(TestCase):
    def test_modulo_serialization(self):
        curso = Curso.objects.create(
            titulo="Curso de IA",
            descripcion="Curso introductorio de IA"
        )
        subcurso = Subcurso.objects.create(curso=curso, nombre="Subcurso Redes Neuronales")
        modulo = Modulo.objects.create(subcurso=subcurso, nombre="Introducción a redes")
        serializer = ModuloSerializer(modulo)
        self.assertEqual(serializer.data["nombre"], "Introducción a redes")


class ContratoSerializerTests(TestCase):
    def test_fecha_validation(self):
        empresa = Empresa.objects.create(
            nombre="Empresa Demo",
            area="Finanzas",
            direccion="Av. Siempre Viva 123",
            telefono="123456789",
            correoElectronico="empresa_demo@example.com",
            numeroEmpleados=100
        )
        instructor = Instructor.objects.create(
            first_name="Carlos",
            last_name="Perez",
            email="instructor@example.com",
            password="Password123",
            empresa=empresa
        )
        curso = Curso.objects.create(titulo="Curso de Redes", descripcion="Redes Avanzadas")
        data = {
            "instructor": instructor.id,
            "curso": curso.id,
            "fechaInicioCapacitacion": "2025-01-01",
            "fechaFinCapacitacion": "2024-12-31",
        }
        serializer = ContratoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("fechaInicioCapacitacion", serializer.errors)

# signals

class ModuloSignalTests(TestCase):
    def test_actualizar_cantidad_modulos_y_progreso(self):
        curso = Curso.objects.create(titulo="Curso de Prueba", descripcion="Prueba de señales")
        subcurso = Subcurso.objects.create(curso=curso, nombre="Subcurso de Prueba")

        self.assertEqual(subcurso.cantidad_modulos, 0)  

        Modulo.objects.create(subcurso=subcurso, nombre="Módulo 1")
        subcurso.refresh_from_db()
        self.assertEqual(subcurso.cantidad_modulos, 1) 


class CertificadoSignalTests(TestCase):
    def test_emitir_certificado_automatico(self):

        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            area="Educación",
            direccion="Calle Real 456",
            telefono="987654321",
            correoElectronico="empresa_test@example.com",
            numeroEmpleados=100
        )
        instructor = Instructor.objects.create(
            first_name="Instructor",
            last_name="Uno",
            email="instructor@example.com",
            password="Password123",
            empresa=empresa
        )
        curso = Curso.objects.create(
            titulo="Curso de Certificación",
            descripcion="Curso de prueba"
        )
        contrato = Contrato.objects.create(
            instructor=instructor,
            curso=curso,
            codigoOrganizacion="ORG123",
            fechaInicioCapacitacion="2024-01-01",
            fechaFinCapacitacion="2024-12-31"
        )
        estudiante = Estudiante.objects.create(
            first_name="Estudiante",
            last_name="Uno",
            email="test@example.com",
            password="Password123",
            codigoOrganizacion="ORG123"
        )

        
        self.assertEqual(Certificado.objects.count(), 0)


        Progreso.objects.create(estudiante=estudiante, curso=curso, completado=True)

        self.assertEqual(Certificado.objects.count(), 1)

class ModuloProgresoSignalTests(TestCase):
    def test_actualizar_progreso_con_modulo(self):
        
        empresa = Empresa.objects.create(
            nombre="Empresa Test",
            area="Educación",
            direccion="Calle Real 456",
            telefono="987654321",
            correoElectronico="empresa_test@example.com",
            numeroEmpleados=100
        )
        instructor = Instructor.objects.create(
            first_name="Instructor",
            last_name="Uno",
            email="instructor@example.com",
            password="Password123",
            empresa=empresa
        )
        curso = Curso.objects.create(
            titulo="Curso Modular",
            descripcion="Prueba de progreso"
        )
        contrato = Contrato.objects.create(
            instructor=instructor,
            curso=curso,
            codigoOrganizacion="ORG123",
            fechaInicioCapacitacion="2024-01-01",
            fechaFinCapacitacion="2024-12-31"
        )
        subcurso = Subcurso.objects.create(curso=curso, nombre="Subcurso Modular")
        modulo1 = Modulo.objects.create(subcurso=subcurso, nombre="Módulo 1")
        modulo2 = Modulo.objects.create(subcurso=subcurso, nombre="Módulo 2")
        estudiante = Estudiante.objects.create(
            first_name="Estudiante",
            last_name="Uno",
            email="test@example.com",
            password="Password123",
            codigoOrganizacion="ORG123"
        )

       
        EstudianteModulo.objects.create(estudiante=estudiante, modulo=modulo1, completado=True)
        estudiante_subcurso = EstudianteSubcurso.objects.get(estudiante=estudiante, subcurso=subcurso)
        self.assertEqual(estudiante_subcurso.porcentajeCompletado, 50) 

        
        EstudianteModulo.objects.create(estudiante=estudiante, modulo=modulo2, completado=True)
        estudiante_subcurso.refresh_from_db()
        self.assertEqual(estudiante_subcurso.porcentajeCompletado, 100)  


class SubcursoSignalTests(TestCase):
    def test_actualizar_cantidad_subcursos(self):
        curso = Curso.objects.create(titulo="Curso con Subcursos", descripcion="Prueba de subcursos")
        self.assertEqual(curso.cantidadSubcursos, 0) 

        Subcurso.objects.create(curso=curso, nombre="Subcurso 1")
        curso.refresh_from_db()
        self.assertEqual(curso.cantidadSubcursos, 1) 


