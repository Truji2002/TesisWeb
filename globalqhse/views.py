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
from drf_yasg import openapi
import logging
from .models import (
    Usuario, Administrador, Instructor, Estudiante,
    Simulacion, Curso, Subcurso, Modulo, Empresa
)
from .serializers import (
    UsuarioSerializer, AdministradorSerializer, InstructorSerializer, EstudianteSerializer,
    CursoSerializer, AdministradorDetailSerializer, InstructorDetailSerializer,
    ClienteDetailSerializer, LoginResponseSerializer, SimulacionSerializer,
    SubcursoSerializer, ModuloSerializer, EmpresaSerializer,RegisterInstructorSerializer
)
from .utils.email import EmailService

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
                'fechaInicioCapacitacion': openapi.Schema(type=openapi.FORMAT_DATE, description='Fecha de inicio de la capacitación'),
                'fechaFinCapacitacion': openapi.Schema(type=openapi.FORMAT_DATE, description='Fecha de fin de la capacitación'),
            },
            required=['instructor_anterior_id', 'nombre', 'apellido', 'email', 'fechaInicioCapacitacion', 'fechaFinCapacitacion']
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
            fechaInicioCapacitacion = request.data.get('fechaInicioCapacitacion')
            fechaFinCapacitacion = request.data.get('fechaFinCapacitacion')

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
                fechaInicioCapacitacion=fechaInicioCapacitacion,
                fechaFinCapacitacion=fechaFinCapacitacion
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
            }
        ),
        responses={200: 'Detalle del usuario autenticado con token', 401: 'Credenciales inválidas'}
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_active:
                # Identificar el rol del usuario
                if user.rol == 'admin':
                    serializer = AdministradorDetailSerializer(user)
                elif user.rol == 'instructor':
                    serializer = InstructorDetailSerializer(user)
                elif user.rol == 'estudiante':
                    serializer = ClienteDetailSerializer(user)
                else:
                    serializer = LoginResponseSerializer(user)

                refresh = RefreshToken.for_user(user)

                response_data = serializer.data
                response_data['refresh'] = str(refresh)
                response_data['access'] = str(refresh.access_token)

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Cuenta desactivada'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)


class CursoViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]


class SubcursoViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Subcurso.objects.all()
    serializer_class = SubcursoSerializer
    permission_classes = [IsAuthenticated]


class ModuloViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Modulo.objects.all()
    serializer_class = ModuloSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

class SimulacionViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Simulacion.objects.all()
    serializer_class = SimulacionSerializer
    permission_classes = [IsAuthenticated] 

@api_view(['POST'])
def completar_modulo(request, modulo_id):
    """Vista para marcar un módulo como completado y actualizar el progreso del subcurso."""
    modulo = get_object_or_404(Modulo, id=modulo_id)
    modulo.completado = True
    modulo.save()

    # Actualizar progreso del subcurso
    modulo.subcurso.actualizar_progreso()

    return Response({'message': 'Módulo completado y progreso actualizado'}, status=status.HTTP_200_OK)
