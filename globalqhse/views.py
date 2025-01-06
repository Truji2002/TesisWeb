from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from drf_yasg import openapi
from rest_framework import generics
from django.db import transaction
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend

from datetime import date

import logging
from .models import (
    Usuario, Administrador, Instructor, Estudiante,
    Curso, Subcurso, Modulo, Empresa, InstructorCurso,Progreso,Certificado,EstudiantePrueba, Prueba, Pregunta
)
from .serializers import (
    UsuarioSerializer, AdministradorSerializer, InstructorSerializer, EstudianteSerializer,
    CursoSerializer, AdministradorDetailSerializer, InstructorDetailSerializer,
    EstudianteDetailSerializer, LoginResponseSerializer, EstudiantePruebaSerializer,  PruebaSerializer, PreguntaSerializer,PruebaConPreguntasSerializer,PreguntaParaPruebaExistenteSerializer,
    SubcursoSerializer, ModuloSerializer, EmpresaSerializer,RegisterInstructorSerializer,InstructorCursoSerializer,ProgresoSerializer
)
from .utils.email import EmailService
from django.http import FileResponse, Http404, HttpResponse

logger = logging.getLogger(__name__)

class EmpresaViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsAdminUser]
    @swagger_auto_schema(
    operation_description="Buscar empresas por nombre. El parámetro de búsqueda es insensible a mayúsculas y minúsculas.",
    manual_parameters=[
        openapi.Parameter(
            'nombre',
            openapi.IN_QUERY,
            description="Nombre (o parte del nombre) de la empresa a buscar",
            type=openapi.TYPE_STRING,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Lista de empresas que coinciden con el nombre",
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID de la empresa"),
                        'nombre': openapi.Schema(type=openapi.TYPE_STRING, description="Nombre de la empresa"),
                        'area': openapi.Schema(type=openapi.TYPE_STRING, description="Área de la empresa"),
                        'direccion': openapi.Schema(type=openapi.TYPE_STRING, description="Dirección de la empresa"),
                        'telefono': openapi.Schema(type=openapi.TYPE_STRING, description="Teléfono de la empresa"),
                        'correoElectronico': openapi.Schema(type=openapi.TYPE_STRING, description="Correo electrónico de la empresa"),
                        'numeroEmpleados': openapi.Schema(type=openapi.TYPE_INTEGER, description="Número de empleados"),
                    }
                )
            )
        ),
        400: "El parámetro 'nombre' es requerido",
    }
)
    @action(detail=False, methods=['get'], url_path='buscar-por-nombre')
    def buscar_por_nombre(self, request):
        """
        Filtra empresas por su nombre.
        """
        nombre = request.query_params.get('nombre', None)
        if nombre:
            empresas = self.queryset.filter(nombre__icontains=nombre)
            serializer = self.get_serializer(empresas, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "El parámetro 'nombre' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )


class UsuarioViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]


class AdministradorViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Administrador.objects.all()
    serializer_class = AdministradorSerializer
    permission_classes = [IsAdminUser]
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def crear(self, request):
        serializer = AdministradorSerializer(data=request.data)
        if serializer.is_valid():
            administrador = serializer.save()
            administrador.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstructorViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Filtra instructores por estado activo o inactivo.",
        manual_parameters=[
            openapi.Parameter(
                'is_active',  # Nombre del parámetro
                openapi.IN_QUERY,  # Tipo: Query parameter
                description="Filtra por estado: 'true' para activos, 'false' para inactivos",
                type=openapi.TYPE_BOOLEAN,  # Tipo de dato
            )
        ],
        responses={
            200: InstructorSerializer(many=True),
            400: "Parámetro inválido",
        },
    )
    @action(detail=False, methods=['get'], url_path='filtrar')
    def filtrar(self, request):
        estado = request.query_params.get('is_active', None)
        if estado is not None:
            queryset = self.queryset.filter(is_active=estado.lower() == 'true')
        else:
            queryset = self.queryset

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instructor = serializer.save()
            temp_password = instructor.generar_contraseña_temporal()

            # Enviar correo con contraseña temporal
            email_service = EmailService(
                to_email=instructor.email,
                subject='Bienvenido a la organización',
                body=f"""
                Hola {instructor.first_name},

                Su cuenta ha sido creada exitosamente. Aquí están sus credenciales de acceso:

                - Código de organización: {instructor.codigoOrganizacion}
                - Contraseña temporal:  {temp_password}

                Por favor, cambie su contraseña después de iniciar sesión.

                Saludos,
                Global QHSE
                """
            )
            email_service.send_email()

            response_data = serializer.data
            response_data['temp_password'] = temp_password
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        try:
            instructor = Instructor.objects.get(pk=pk)
            data = request.data

            # Actualizar estado activo/inactivo
            is_active = data.get('is_active')
            if is_active is not None:
                instructor.is_active = is_active

                # Actualizar estado de los estudiantes relacionados
                Estudiante.objects.filter(codigoOrganizacion=instructor.codigoOrganizacion).update(is_active=is_active)

            # Actualizar otros campos del instructor
            serializer = InstructorSerializer(instructor, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Instructor actualizado correctamente.", "instructor": serializer.data},
                    status=status.HTTP_200_OK,
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Instructor.DoesNotExist:
            return Response({"error": "Instructor no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
    @swagger_auto_schema(
        operation_description="Busca instructores asociados a una empresa por su ID.",
        manual_parameters=[
            openapi.Parameter(
                'empresa_id',  # Nombre del parámetro
                openapi.IN_QUERY,  # Tipo: Query parameter
                description="ID de la empresa para filtrar instructores",
                type=openapi.TYPE_INTEGER,  # Tipo de dato
            )
        ],
        responses={
            200: InstructorSerializer(many=True),
            400: "Parámetro inválido",
        },
    )
    @action(detail=False, methods=['get'], url_path='buscar-por-empresa')
    def buscar_por_empresa(self, request):
        """
        Filtra instructores según el ID de la empresa.
        """
        empresa_id = request.query_params.get('empresa_id', None)
        if empresa_id is None:
            return Response(
                {"error": "El parámetro 'empresa_id' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Filtrar instructores por empresa
            queryset = self.queryset.filter(empresa__id=empresa_id)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError:
            return Response(
                {"error": "El parámetro 'empresa_id' debe ser un número entero válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

class RegisterInstructorAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Registrar un nuevo instructor. Genera automáticamente la contraseña y el código de organización.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del instructor'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Apellido del instructor'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Correo electrónico'),
                'area': openapi.Schema(type=openapi.TYPE_STRING, description='Área de especialización'),
                'fechaInicioCapacitacion': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Fecha de inicio de la capacitación'),
                'fechaFinCapacitacion': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Fecha de fin de la capacitación'),
                'empresa': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la empresa a la que pertenece el instructor'),
            },
            required=['first_name', 'last_name', 'email', 'area', 'fechaInicioCapacitacion', 'fechaFinCapacitacion', 'empresa']
        ),
        responses={
            201: "Instructor creado exitosamente.",
            400: "Error de validación.",
            500: "Error interno del servidor."
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = RegisterInstructorSerializer(data=request.data)
        if serializer.is_valid():
            instructor = serializer.save()
            return Response({
                "message": "Instructor creado exitosamente.",
                "data": {
                    "id": instructor.id,
                    "first_name": instructor.first_name,
                    "last_name": instructor.last_name,
                    "email": instructor.email,
                    "codigoOrganizacion": instructor.codigoOrganizacion  # Se devuelve para referencia
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class ModificarInstructorAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    """
    API para reemplazar un instructor por uno nuevo, asignándole una contraseña temporal y enviándola por correo.
    """

    @swagger_auto_schema(
        operation_description="Reemplazar un instructor eliminando al anterior y creando uno nuevo asociado a la misma empresa y codigoOrganizacion.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'instructor_anterior_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del instructor a reemplazar'),
                'nombre': openapi.Schema(type=openapi.TYPE_STRING, description='Nombre del nuevo instructor'),
                'apellido': openapi.Schema(type=openapi.TYPE_STRING, description='Apellido del nuevo instructor'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Correo electrónico del nuevo instructor'),
            },
            required=['instructor_anterior_id', 'nombre', 'apellido', 'email']
        ),
        responses={
            200: openapi.Response("Instructor reemplazado exitosamente."),
            400: "Bad Request",
            500: "Error Interno del Servidor"
        }
    )
    def post(self, request, *args, **kwargs):
        try:
            # Obtener datos de la solicitud
            instructor_anterior_id = request.data.get('instructor_anterior_id')
            nombre = request.data.get('nombre')
            apellido = request.data.get('apellido')
            email = request.data.get('email')
            

            # Obtener el instructor anterior
            instructor_anterior = Instructor.objects.get(id=instructor_anterior_id)

            # Crear el nuevo instructor
            nuevo_instructor = Instructor.objects.create(
                first_name=nombre,
                last_name=apellido,
                email=email,
                area=instructor_anterior.area,
                codigoOrganizacion=instructor_anterior.codigoOrganizacion,
                empresa=instructor_anterior.empresa,
                fechaInicioCapacitacion=instructor_anterior.fechaInicioCapacitacion,
                fechaFinCapacitacion=instructor_anterior.fechaFinCapacitacion,
                debeCambiarContraseña=True
            )

            # Generar una contraseña temporal para el nuevo instructor
            temp_password = nuevo_instructor.generar_contraseña_temporal()

            # Enviar correo al nuevo instructor
            email_service = EmailService(
                to_email=nuevo_instructor.email,
                subject='Bienvenido a la organización',
                body=f"""
                Hola {nuevo_instructor.first_name},

                Su cuenta ha sido creada exitosamente. Aquí están sus credenciales de acceso:

                - Código de organización: {nuevo_instructor.codigoOrganizacion}
                - Contraseña temporal: {temp_password}

                Por favor, cambie su contraseña después de iniciar sesión.

                Saludos,
                Global QHSE
                """
            )
            email_service.send_email()

            # Eliminar el instructor anterior
            instructor_anterior.delete()

            return Response({"message": f"Instructor {instructor_anterior.email} reemplazado por {nuevo_instructor.email}."}, status=status.HTTP_200_OK)

        except Instructor.DoesNotExist:
            return Response({"error": "El instructor anterior no existe."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EstudianteViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer
    

    @action(detail=False, methods=['post'])
    def crear(self, request):
        serializer = EstudianteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    @swagger_auto_schema(
        operation_description="Filtra estudiantes por código de organización.",
        manual_parameters=[
            openapi.Parameter(
                'codigoOrganizacion',  # Nombre del parámetro
                openapi.IN_QUERY,  # Tipo: Query parameter
                description="Código de organización para filtrar estudiantes",
                type=openapi.TYPE_STRING,  # Tipo de dato
            )
        ],
        responses={
            200: EstudianteSerializer(many=True),
            400: "Parámetro inválido",
        },
    )
    @action(detail=False, methods=['get'], url_path='filtrar')
    def filtrar_por_codigo(self, request):
        """
        Filtra estudiantes según el código de organización proporcionado en la query string.
        """
        codigo_organizacion = request.query_params.get('codigoOrganizacion', None)
        if codigo_organizacion:
            queryset = self.queryset.filter(codigoOrganizacion=codigo_organizacion)
        else:
            queryset = self.queryset

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegistroEstudianteAPIView(APIView):
    

    """
    API para registrar un estudiante y asignarlo automáticamente a los cursos de su instructor
    basado en el codigoOrganizacion.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Crear un estudiante y asignarlo automáticamente a los cursos de su instructor en base al codigoOrganizacion.",
        request_body=EstudianteSerializer,  # Usamos el serializer para validar los datos
        responses={
            201: openapi.Response(
                'Estudiante creado con éxito',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito'),
                    }
                )
            ),
            400: openapi.Response(
                'Error en los datos enviados',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Descripción del error'),
                    }
                )
            ),
            500: openapi.Response(
                'Error Interno del Servidor',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de error interno'),
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        # Validar los datos de entrada con el serializer
        serializer = EstudianteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Crear el estudiante utilizando los datos validados
            estudiante = Estudiante.crear_estudiante_con_cursos(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                codigoOrganizacion=serializer.validated_data['codigoOrganizacion'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', '')
            )
            return Response({"message": f"Estudiante {estudiante.email} creado exitosamente."}, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Manejo de errores específicos de validación
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Registrar errores inesperados en el logger
            logger.error(f"Error inesperado al registrar estudiante: {str(e)}")
            return Response({"error": "Ocurrió un error inesperado. Por favor, intente más tarde."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Inicia sesión, devuelve el tipo de usuario, sus detalles y un token JWT.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Contraseña'),
            },
            required=['email', 'password']
        ),
        responses={
            200: openapi.Response("Detalle del usuario autenticado con token"),
            401: "Credenciales inválidas",
            403: "Cuenta desactivada"
        }
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            
            if user.is_active:
                # Identificar el rol del usuario
                if user.rol == 'admin':
                    user = Administrador.objects.get(id=user.id)  # Forzar subclase Administrador
                    serializer = AdministradorDetailSerializer(user)
                elif user.rol == 'instructor':
                    user = Instructor.objects.get(id=user.id)  # Forzar subclase Instructor
                    serializer = InstructorDetailSerializer(user)
                elif user.rol == 'estudiante':
                    user = Estudiante.objects.get(id=user.id)  # Forzar subclase Estudiante
                    serializer = EstudianteDetailSerializer(user)
                else:
                    return Response({'error': 'Rol no válido.'}, status=status.HTTP_400_BAD_REQUEST)


                # Generar tokens
                refresh = RefreshToken.for_user(user)

                # Respuesta
                response_data = serializer.data
                response_data['refresh'] = str(refresh)
                response_data['access'] = str(refresh.access_token)

                # Agregar `debeCambiarContraseña` solo si es un instructor
                if user.rol == 'instructor':
                    response_data['debeCambiarContraseña'] = user.debeCambiarContraseña

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Cuenta desactivada'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


class CambiarContraseñaAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Permite al usuario autenticado cambiar su contraseña.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'old_password': openapi.Schema(type=openapi.TYPE_STRING, description='Contraseña actual'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='Nueva contraseña'),
            },
            required=['old_password', 'new_password']
        ),
        responses={
            200: openapi.Response("Contraseña cambiada exitosamente."),
            400: "Error en la solicitud (contraseña incorrecta o campos faltantes)."
        }
    )
    def post(self, request):
        user = request.user  # Usuario autenticado obtenido del token JWT
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        # Validar contraseñas ingresadas
        if not old_password or not new_password:
            return Response({'error': 'Ambos campos (old_password y new_password) son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar que la contraseña antigua sea correcta
        if not user.check_password(old_password):
            return Response({'error': 'La contraseña antigua no es correcta.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.check_password(new_password):
            return Response({'error': 'La nueva contraseña no puede ser igual a la contraseña actual.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Cambiar la contraseña
        user.set_password(new_password)
        user.save()

        # Verificar si es un instructor para actualizar `debeCambiarContraseña`
        if user.rol == 'instructor':
            try:
                instructor = Instructor.objects.get(id=user.id)
                instructor.debeCambiarContraseña = False
                instructor.save()
            except Instructor.DoesNotExist:
                return Response({'error': 'Instructor no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'message': 'Contraseña cambiada exitosamente.'}, status=status.HTTP_200_OK)


class CursoViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        """
        Personaliza el comportamiento al actualizar un curso.
        Si el campo `simulacion` cambia, actualiza los registros de progreso relacionados.
        """
        # Guarda la instancia original antes de la actualización
        curso_anterior = self.get_object()

        # Realiza la actualización
        instance = serializer.save()

        # Si `simulacion` cambió de False a True
        if not curso_anterior.simulacion and instance.simulacion:
            # Actualiza los registros de progreso relacionados
            Progreso.objects.filter(
                curso=instance,
                fechaFinCurso__isnull=True,  # No tienen fecha de finalización
                porcentajeCompletado__lt=100,  # No están al 100%
                simulacionCompletada__isnull=True  # No tienen simulación completada
            ).update(simulacionCompletada=False)

        # Si `simulacion` cambió de True a False
        elif curso_anterior.simulacion and not instance.simulacion:
            # Establece el campo simulacionCompletada como NULL para los registros de progreso relacionados
            Progreso.objects.filter(
                curso=instance
            ).update(simulacionCompletada=None)


class SubcursoViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Subcurso.objects.all()
    serializer_class = SubcursoSerializer
    permission_classes = [IsAuthenticated]

class SubcursosPorCursoAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Obtener subcursos asociados a un curso específico mediante su ID.",
        responses={
            200: openapi.Response("Lista de subcursos", SubcursoSerializer(many=True)),
            404: "Curso no encontrado",
        }
    )
    def get(self, request, curso_id, *args, **kwargs):
        try:
            curso = Curso.objects.get(id=curso_id)
        except Curso.DoesNotExist:
            return Response({"error": "Curso no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        subcursos = Subcurso.objects.filter(curso=curso)
        serializer = SubcursoSerializer(subcursos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ModuloViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Modulo.objects.all()
    serializer_class = ModuloSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

class ModulosPorSubcursoAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Obtener módulos asociados a un subcurso específico mediante su ID.",
        responses={
            200: openapi.Response("Lista de módulos", ModuloSerializer(many=True)),
            404: "Subcurso no encontrado",
        }
    )
    def get(self, request, subcurso_id, *args, **kwargs):
        try:
            subcurso = Subcurso.objects.get(id=subcurso_id)
        except Subcurso.DoesNotExist:
            return Response({"error": "Subcurso no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        modulos = Modulo.objects.filter(subcurso=subcurso)
        # Pasa el request al contexto del serializer
        serializer = ModuloSerializer(modulos, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)





class DescargarArchivoModuloAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Cambia a [AllowAny] si no requiere autenticación

    def get(self, request, pk, *args, **kwargs):
        try:
            # Obtener el módulo por su ID
            modulo = Modulo.objects.get(pk=pk)

            # Verificar si el módulo tiene un archivo asociado
            if not modulo.archivo:
                return Response({"error": "Este módulo no tiene un archivo asociado."}, status=status.HTTP_404_NOT_FOUND)

            # Retornar el archivo como respuesta
            archivo = modulo.archivo.path
            response = FileResponse(open(archivo, 'rb'), content_type='application/octet-stream')
            response['Content-Disposition'] = f'inline; filename="{modulo.archivo.name}"'
            return response

        except Modulo.DoesNotExist:
            raise Http404("Módulo no encontrado.")
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            


class InstructorCursoAPIView(APIView):
    """
    API para gestionar las relaciones entre instructores y cursos.
    """

    @swagger_auto_schema(
        operation_description="Obtiene todas las relaciones entre instructores y cursos o filtra por instructor y curso.",
        manual_parameters=[
            openapi.Parameter('instructor', openapi.IN_QUERY, description="ID del instructor", type=openapi.TYPE_INTEGER),
            openapi.Parameter('curso', openapi.IN_QUERY, description="ID del curso", type=openapi.TYPE_INTEGER),
        ],
        responses={200: InstructorCursoSerializer(many=True)}
    )
    def get(self, request):
        instructor_id = request.query_params.get('instructor')
        curso_id = request.query_params.get('curso')

        # Filtrar por los parámetros proporcionados
        if instructor_id and curso_id:
            relaciones = InstructorCurso.objects.filter(instructor_id=instructor_id, curso_id=curso_id)
        elif instructor_id:
            relaciones = InstructorCurso.objects.filter(instructor_id=instructor_id)
        elif curso_id:
            relaciones = InstructorCurso.objects.filter(curso_id=curso_id)
        else:
            relaciones = InstructorCurso.objects.all()

        serializer = InstructorCursoSerializer(relaciones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Crea una nueva relación entre un instructor y un curso.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'instructor': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del instructor'),
                'curso': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
            },
            required=['instructor', 'curso']
        ),
        responses={
            201: openapi.Response('Relación creada exitosamente.', InstructorCursoSerializer),
            400: 'Error en los datos enviados.',
            500: 'Error interno del servidor.',
        }
    )
    def post(self, request):
        instructor_id = request.data.get('instructor')
        curso_id = request.data.get('curso')

        # Validar datos
        if not instructor_id or not curso_id:
            return Response({"error": "Los campos 'instructor' y 'curso' son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Crear la relación entre instructor y curso
            relacion = InstructorCurso.objects.create(instructor_id=instructor_id, curso_id=curso_id)

            # Obtener el código de organización del instructor
            codigo_organizacion = relacion.instructor.codigoOrganizacion

            # Obtener los estudiantes asociados al código de organización
            estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)

            # Crear los registros de progreso para los estudiantes
            Progreso.objects.bulk_create([
                Progreso(estudiante=estudiante, curso_id=curso_id, completado=False, porcentajeCompletado=0)
                for estudiante in estudiantes
            ])

            return Response({"message": "Relación creada exitosamente."}, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"error": "La relación entre el instructor y el curso ya existe."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="Elimina una relación entre un instructor y un curso.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'instructor': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del instructor'),
                'curso': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
            },
            required=['instructor', 'curso']
        ),
        responses={
            200: openapi.Response('Relación eliminada exitosamente.'),
            400: 'Error en los datos enviados.',
            404: 'Relación no encontrada.',
        }
    )
    def delete(self, request):
        instructor_id = request.data.get('instructor')
        curso_id = request.data.get('curso')

        if not instructor_id or not curso_id:
            return Response({"error": "Los campos 'instructor' y 'curso' son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Obtener la relación
            relacion = InstructorCurso.objects.get(instructor_id=instructor_id, curso_id=curso_id)

            # Obtener el código de organización del instructor
            codigo_organizacion = relacion.instructor.codigoOrganizacion

            # Obtener los estudiantes asociados al código de organización
            estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)

            # Eliminar los registros de progreso relacionados con los estudiantes y el curso
            Progreso.objects.filter(estudiante__in=estudiantes, curso_id=curso_id).delete()

            # Eliminar la relación entre instructor y curso
            relacion.delete()

            return Response({"message": "Relación eliminada exitosamente."}, status=status.HTTP_200_OK)
        except InstructorCurso.DoesNotExist:
            return Response({"error": "La relación entre el instructor y el curso no fue encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class EstudiantesPorCodigoOrganizacionAPIView(APIView):
    """
    API para buscar estudiantes por código de organización.
    """
    @swagger_auto_schema(
        operation_description="Busca estudiantes asociados a un código de organización.",
        manual_parameters=[
            openapi.Parameter(
                'codigoOrganizacion',
                openapi.IN_QUERY,
                description="Código de organización del instructor",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response("Estudiantes encontrados.", EstudianteSerializer(many=True)),
            400: "Código de organización no proporcionado.",
            404: "No se encontraron estudiantes para el código de organización proporcionado.",
        }
    )
    def get(self, request):
        codigo_organizacion = request.query_params.get('codigoOrganizacion')

        # Validar que el parámetro sea proporcionado
        if not codigo_organizacion:
            return Response(
                {"error": "El parámetro 'codigoOrganizacion' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar estudiantes por código de organización
        estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)

        if estudiantes.exists():
            serializer = EstudianteSerializer(estudiantes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "No se encontraron estudiantes para el código de organización proporcionado."},
                status=status.HTTP_404_NOT_FOUND
            )
        

class ProgresoViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Progreso.objects.all()
    serializer_class = ProgresoSerializer
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Obtiene los registros de progreso. Si se proporciona `estudiante_id`, filtra los registros por el ID del estudiante.",
        manual_parameters=[
            openapi.Parameter(
                'estudiante_id', 
                openapi.IN_QUERY, 
                description="Filtra los registros de progreso por ID del estudiante.", 
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={200: ProgresoSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        """
        Documentación del método list para incluir `estudiante_id` como filtro.
        """
        return super().list(request, *args, **kwargs)
    def get_queryset(self):
        """
        Filtra los registros de progreso por `estudiante_id` si se proporciona como parámetro.
        """
        estudiante_id = self.request.query_params.get('estudiante_id')  # Capturar el parámetro `estudiante_id`
        if estudiante_id:
            return Progreso.objects.filter(estudiante_id=estudiante_id)
        return super().get_queryset()  # Devuelve todos los registros si no hay filtro

class EstudiantePruebaViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = EstudiantePrueba.objects.all()
    serializer_class = EstudiantePruebaSerializer
    permission_classes = [IsAuthenticated]


class EmitirCertificadoAPIView(APIView):
    """
    API para emitir un certificado basado en el progreso del estudiante.
    """
    @swagger_auto_schema(
        operation_description="Emitir un certificado para un estudiante basado en el progreso completado del curso.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del estudiante'),
                'curso_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
            },
            required=['estudiante_id', 'curso_id']
        ),
        responses={
            201: openapi.Response("Certificado emitido exitosamente."),
            200: openapi.Response("El certificado ya ha sido emitido."),
            400: openapi.Response("Error en los datos o progreso incompleto."),
            404: openapi.Response("Estudiante o curso no encontrado."),
        }
    )
    def post(self, request):
        estudiante_id = request.data.get('estudiante_id')
        curso_id = request.data.get('curso_id')

        # Validar los parámetros
        if not estudiante_id or not curso_id:
            return Response({"error": "Los campos 'estudiante_id' y 'curso_id' son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener estudiante y curso
        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)
            curso = Curso.objects.get(id=curso_id)
        except Estudiante.DoesNotExist:
            return Response({"error": "Estudiante no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Curso.DoesNotExist:
            return Response({"error": "Curso no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Emitir el certificado
        resultado = Certificado.emitir_certificado(estudiante, curso)
        if resultado == "El estudiante no ha completado el curso.":
            return Response({"error": resultado}, status=status.HTTP_400_BAD_REQUEST)
        if resultado == "El certificado ya ha sido emitido.":
            return Response({"message": resultado}, status=status.HTTP_200_OK)

        return Response({"message": resultado}, status=status.HTTP_201_CREATED)
        
class PruebaViewSet(viewsets.ModelViewSet):
    queryset = Prueba.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PruebaSerializer

    def create(self, request, *args, **kwargs):
        curso_id = request.data.get('curso')
        if Prueba.objects.filter(curso_id=curso_id).exists():
            return Response(
                {"error": "Ya existe una prueba asociada a este curso."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)
    @action(detail=False, methods=['get'], url_path='by_curso/(?P<curso_id>[^/.]+)')
    def get_prueba_by_curso(self, request, curso_id=None):
        try:
            prueba = Prueba.objects.get(curso__id=curso_id)
            serializer = self.get_serializer(prueba)
            return Response(serializer.data)
        except Prueba.DoesNotExist:
            return Response({"detail": "Prueba no encontrada para el curso especificado."}, status=status.HTTP_404_NOT_FOUND)
    @action(detail=True, methods=['post'], url_path='add_preguntas')
    def add_preguntas(self, request, pk=None):
        """
        Agregar preguntas a una prueba específica.
        """
        try:
            prueba = self.get_object()  # Obtener la prueba por su ID
            preguntas_data = request.data  # Datos enviados en la solicitud

            # Verificar si los datos son una lista
            if not isinstance(preguntas_data, list):
                return Response(
                    {"error": "El cuerpo de la solicitud debe ser una lista de preguntas."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Crear preguntas asociadas a la prueba
            for pregunta_data in preguntas_data:
                pregunta_data['prueba'] = prueba.id  # Asignar la prueba a la pregunta
                serializer = PreguntaSerializer(data=pregunta_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            return Response({"message": "Preguntas agregadas con éxito."}, status=status.HTTP_201_CREATED)

        except Prueba.DoesNotExist:
            return Response({"error": "Prueba no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class PreguntaViewSet(viewsets.ModelViewSet):
    queryset = Pregunta.objects.all()
    serializer_class = PreguntaSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['prueba']  #

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):  # Verificar si el cuerpo es una lista
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)
    

class PreguntaListView(generics.ListAPIView):
    serializer_class = PreguntaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        prueba_id = self.request.query_params.get('prueba')
        if prueba_id:
            return Pregunta.objects.filter(prueba_id=prueba_id)
        return Pregunta.objects.none()

@api_view(['POST'])
def completar_modulo(request, modulo_id):
    """Vista para marcar un módulo como completado y actualizar el progreso del subcurso."""
    modulo = get_object_or_404(Modulo, id=modulo_id)
    modulo.completado = True
    modulo.save()

    # Actualizar progreso del subcurso
    modulo.subcurso.actualizar_progreso()

    return Response({'message': 'Módulo completado y progreso actualizado'}, status=status.HTTP_200_OK)

class CertificadoAPIView(APIView):
    """
    API para obtener información de un certificado específico.
    Recibe `curso_id` y `estudiante_id` como parámetros.
    """

    @swagger_auto_schema(
        operation_description="Obtiene un certificado específico basado en el curso y el estudiante.",
        manual_parameters=[
            openapi.Parameter(
                'curso_id', openapi.IN_QUERY, description="ID del curso",
                type=openapi.TYPE_INTEGER, required=True
            ),
            openapi.Parameter(
                'estudiante_id', openapi.IN_QUERY, description="ID del estudiante",
                type=openapi.TYPE_INTEGER, required=True
            ),
        ],
        responses={
            200: "Certificado PDF enviado como respuesta",
            400: openapi.Response(
                "Faltan parámetros",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción del error"),
                    }
                )
            ),
            404: openapi.Response(
                "Certificado no encontrado",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción del error"),
                    }
                )
            )
        }
    )
    def get(self, request):
        # Obtener los parámetros de la solicitud
        curso_id = request.query_params.get('curso_id')
        estudiante_id = request.query_params.get('estudiante_id')

        # Validar que se pasen los parámetros requeridos
        if not curso_id or not estudiante_id:
            return Response(
                {"error": "Se requieren los parámetros 'curso_id' y 'estudiante_id'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar el certificado
        try:
            certificado = Certificado.objects.get(curso_id=curso_id, estudiante_id=estudiante_id)
        except Certificado.DoesNotExist:
            return Response(
                {"error": "No se encontró un certificado para el curso y estudiante especificados."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar si el certificado tiene un archivo PDF asociado
        if not certificado.archivoPdf:
            return Response(
                {"error": "El certificado no tiene un archivo PDF asociado."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Leer el archivo PDF y enviarlo como respuesta
        pdf_path = certificado.archivoPdf.path
        try:
            with open(pdf_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{certificado.archivoPdf.name}"'
                return response
        except FileNotFoundError:
            return Response(
                {"error": "El archivo PDF no se encontró en el servidor."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ActualizarEstudiantePruebaAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Califica una prueba basada en las respuestas del estudiante.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del estudiante"),
                'prueba_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID de la prueba"),
                'respuestas': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="Respuestas del estudiante, con el ID de la pregunta como clave y la respuesta seleccionada como valor."
                ),
            },
            required=['estudiante_id', 'prueba_id', 'respuestas']
        ),
        responses={
            200: "Prueba calificada exitosamente.",
            400: "Error en la calificación."
        }
    )
    def post(self, request):
        estudiante_id = request.data.get('estudiante_id')
        prueba_id = request.data.get('prueba_id')
        respuestas = request.data.get('respuestas')

        if not estudiante_id or not prueba_id or not respuestas:
            return Response(
                {"error": "Estudiante, prueba y respuestas son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        estudiante_prueba = get_object_or_404(EstudiantePrueba, estudiante_id=estudiante_id, prueba_id=prueba_id)

        estudiante_prueba.calificar(respuestas)

        return Response({
            "calificacion": estudiante_prueba.calificacion,
            "estaAprobado": estudiante_prueba.estaAprobado
        }, status=status.HTTP_200_OK)




class PruebasEstudianteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        estudiante_id = request.user.id  # Asume que el usuario autenticado es un estudiante
        pruebas = EstudiantePrueba.objects.filter(estudiante_id=estudiante_id).select_related('prueba')

        data = [
            {
                "id": prueba.prueba.id,
                "curso": prueba.prueba.curso.titulo,
                "duracion": prueba.prueba.duracion,
                "estaAprobado": prueba.estaAprobado,
                "calificacion": prueba.calificacion,
                "fechaPrueba": prueba.fechaPrueba
            }
            for prueba in pruebas
        ]
        return Response(data)


class ResponderPruebaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="API para que un estudiante responda una prueba.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'prueba_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER, 
                    description="ID de la prueba que se va a responder."
                ),
                'respuestas': openapi.Schema(
                    type=openapi.TYPE_OBJECT, 
                    description="Diccionario con las respuestas del estudiante. Las claves son los IDs de las preguntas y los valores son las respuestas seleccionadas.",
                    additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
                ),
            },
            required=['prueba_id', 'respuestas'],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'calificacion': openapi.Schema(
                        type=openapi.TYPE_NUMBER, 
                        description="Calificación obtenida en la prueba."
                    ),
                    'estaAprobado': openapi.Schema(
                        type=openapi.TYPE_BOOLEAN, 
                        description="Indica si el estudiante aprobó la prueba."
                    ),
                    'mensaje': openapi.Schema(
                        type=openapi.TYPE_STRING, 
                        description="Mensaje indicando el resultado de la operación."
                    ),
                },
            ),
            400: "Error en los datos enviados.",
            401: "No autenticado.",
            404: "Prueba no encontrada.",
        }
    )
    def post(self, request):
        prueba_id = request.data.get('prueba_id')
        respuestas = request.data.get('respuestas')

        if not prueba_id or not respuestas:
            return Response(
                {"error": "prueba_id y respuestas son obligatorios."},
                status=400
            )

        estudiante_id = request.user.id
        estudiante_prueba = get_object_or_404(EstudiantePrueba, estudiante_id=estudiante_id, prueba_id=prueba_id)

        # Validar respuestas
        preguntas = Pregunta.objects.filter(prueba_id=prueba_id)
        calificacion_total = 0
        puntos_por_pregunta = preguntas.first().puntajePregunta  # Supone que todas las preguntas tienen el mismo puntaje

        for pregunta in preguntas:
            respuesta_correcta = pregunta.respuestaCorrecta
            respuesta_del_estudiante = respuestas.get(str(pregunta.id))  # Clave debe ser un string

            if respuesta_del_estudiante and respuesta_del_estudiante.lower() == respuesta_correcta.lower():
                calificacion_total += puntos_por_pregunta

        # Guardar calificación
        estudiante_prueba.calificacion = calificacion_total
        estudiante_prueba.estaAprobado = calificacion_total >= 60  # Nota mínima para aprobar
        estudiante_prueba.save()

        return Response({
            "calificacion": estudiante_prueba.calificacion,
            "estaAprobado": estudiante_prueba.estaAprobado,
            "mensaje": "Prueba calificada exitosamente."
        }, status=200)

class PreguntasPorPruebaEstudianteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Obtiene las preguntas de una prueba asignada a un estudiante.",
        manual_parameters=[
            openapi.Parameter(
                'prueba_id',
                openapi.IN_QUERY,
                description="ID de la prueba.",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                "Preguntas de la prueba.",
                PreguntaSerializer(many=True)
            ),
            404: "Prueba no encontrada o no asignada al estudiante."
        }
    )
    def get(self, request):
        prueba_id = request.query_params.get('prueba_id')
        estudiante_id = request.user.id

        if not prueba_id:
            return Response({"error": "El parámetro 'prueba_id' es obligatorio."}, status=400)

        # Verificar si la prueba está asignada al estudiante
        estudiante_prueba = EstudiantePrueba.objects.filter(
            prueba_id=prueba_id, estudiante_id=estudiante_id
        ).first()

        if not estudiante_prueba:
            return Response(
                {"error": "La prueba no está asignada a este estudiante o no existe."},
                status=404
            )

        # Obtener las preguntas asociadas a la prueba
        preguntas = Pregunta.objects.filter(prueba_id=prueba_id)
        serializer = PreguntaSerializer(preguntas, many=True)

        return Response(serializer.data, status=200)

class PreguntasPorPruebaAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Obtiene las preguntas asociadas a una prueba específica.",
        manual_parameters=[
            openapi.Parameter(
                "prueba_id", openapi.IN_QUERY, description="ID de la prueba", type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: PreguntaSerializer(many=True),
            404: "Prueba no encontrada.",
        },
    )
    def get(self, request):
        prueba_id = request.query_params.get("prueba_id")
        if not prueba_id:
            return Response({"error": "El parámetro 'prueba_id' es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        preguntas = Pregunta.objects.filter(prueba_id=prueba_id)
        if not preguntas.exists():
            return Response({"error": "No se encontraron preguntas para esta prueba."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PreguntaSerializer(preguntas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
