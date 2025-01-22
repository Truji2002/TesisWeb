import traceback
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
from django.db.models import Avg
from django.utils.timezone import now
from django.db.models import Q
from django.utils.dateparse import parse_date			 
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date
from django.db.models import Q
import random
import string
import logging
from .models import (
    Usuario, Administrador, Instructor, Estudiante,
    Curso, Subcurso, Modulo, Empresa, Contrato,Progreso,Certificado,EstudiantePrueba, Prueba, Pregunta,EstudianteModulo,EstudianteSubcurso
)
from .serializers import (
    UsuarioSerializer, AdministradorSerializer, InstructorSerializer, EstudianteSerializer,
    CursoSerializer, AdministradorDetailSerializer, InstructorDetailSerializer,
    EstudianteDetailSerializer, LoginResponseSerializer, EstudiantePruebaSerializer,  PruebaSerializer, PreguntaSerializer,PruebaConPreguntasSerializer,PreguntaParaPruebaExistenteSerializer,EstudianteModuloSerializer,EstudianteSubcursoSerializer,
    SubcursoSerializer, ModuloSerializer, EmpresaSerializer,RegisterInstructorSerializer,ContratoSerializer,ProgresoSerializer
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

class VRLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Inicia sesión en el aplicativo VR, verifica si el estudiante tiene un registro en progreso para el curso.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email del estudiante'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Contraseña del estudiante'),
                'curso_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
            },
            required=['email', 'password', 'curso_id']
        ),
        responses={
            200: openapi.Response(
                "Autenticación exitosa",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito'),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Token de actualización JWT'),
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='Token de acceso JWT'),
                        'curso_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
                        'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del estudiante'),
                    }
                )
            ),
            401: "Credenciales inválidas",
            403: "Estudiante no cuenta con una simulación asignada",
            404: "Estudiante no encontrado",
        }
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        curso_id = request.data.get('curso_id')

        
        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_active and user.rol == 'estudiante':
                try:
                    
                    estudiante = Estudiante.objects.get(id=user.id)

                    
                    curso = Curso.objects.filter(id=curso_id, simulacion=True).first()
                    if not curso:
                        return Response(
                            {'error': 'El curso no tiene una simulación asignada.'},
                            status=status.HTTP_403_FORBIDDEN
                        )

                    
                    progreso = Progreso.objects.filter(
                        estudiante=estudiante,
                        curso_id=curso_id,
                        completado=False
                    ).first()

                    if not progreso:
                        return Response(
                            {'error': 'El estudiante no tiene un progreso activo para el curso.'},
                            status=status.HTTP_403_FORBIDDEN
                        )

                    
                    refresh = RefreshToken.for_user(user)

                    return Response(
                        {
                            "message": "Autenticación exitosa.",
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                            "curso_id": curso_id,
                            "estudiante_id": estudiante.id,
                        },
                        status=status.HTTP_200_OK
                    )
                except Estudiante.DoesNotExist:
                    return Response({'error': 'No se encontró al estudiante.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(
                    {'error': 'Credenciales inválidas o usuario no autorizado.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            return Response({'error': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)
        

class EliminarContratosAPIView(APIView):
    """
    API para eliminar todos los contratos asociados a un `codigoOrganizacion`.
    """
    @swagger_auto_schema(
        operation_description="Elimina todos los contratos asociados a un código de organización.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'codigoOrganizacion': openapi.Schema(type=openapi.TYPE_STRING, description="Código de organización"),
            },
            required=['codigoOrganizacion']
        ),
        responses={
            200: "Contratos eliminados exitosamente.",
            400: "Error en los datos enviados.",
            500: "Error interno del servidor.",
        }
    )
    def delete(self, request):
        codigo_organizacion = request.data.get('codigoOrganizacion')
 
        if not codigo_organizacion:
            return Response({"error": "El campo 'codigoOrganizacion' es requerido."}, status=status.HTTP_400_BAD_REQUEST)
 
        try:
            with transaction.atomic():
                contratos = Contrato.objects.filter(codigoOrganizacion=codigo_organizacion)
 
                if not contratos.exists():
                    return Response({"error": "No se encontraron contratos con el código de organización especificado."},
                                    status=status.HTTP_404_NOT_FOUND)
 
                
                cursos_ids = contratos.values_list('curso_id', flat=True)
 
                
                estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)
 
                
                Progreso.objects.filter(estudiante__in=estudiantes, curso_id__in=cursos_ids).delete()
                pruebas = Prueba.objects.filter(curso_id__in=cursos_ids)
                EstudiantePrueba.objects.filter(estudiante__in=estudiantes, prueba__in=pruebas).delete()
                subcursos = Subcurso.objects.filter(curso_id__in=cursos_ids)
                EstudianteSubcurso.objects.filter(estudiante__in=estudiantes, subcurso__in=subcursos).delete()
                modulos = Modulo.objects.filter(subcurso__in=subcursos)
                EstudianteModulo.objects.filter(estudiante__in=estudiantes, modulo__in=modulos).delete()
 
                
                contratos.delete()
 
                return Response({"message": "Contratos y registros relacionados eliminados exitosamente."}, status=status.HTTP_200_OK)
 
        except Exception as e:
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InstructorViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="Filtra instructores por estado activo o inactivo.",
        manual_parameters=[
            openapi.Parameter(
                'is_active',  
                openapi.IN_QUERY,  
                description="Filtra por estado: 'true' para activos, 'false' para inactivos",
                type=openapi.TYPE_BOOLEAN,  
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
      
	
		
    @swagger_auto_schema(
        operation_description="Busca instructores asociados a una empresa por su ID.",
        manual_parameters=[
            openapi.Parameter(
                'empresa_id',  
                openapi.IN_QUERY,
                description="ID de la empresa para filtrar instructores",
                type=openapi.TYPE_INTEGER,
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
																										  
																																					  
																																				
                'empresa': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID de la empresa a la que pertenece el instructor'),
            },
            required=['first_name', 'last_name', 'email','empresa']
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
                    
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class ModificarInstructorAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    """
    API para reemplazar un instructor reasignando contratos y notificando en un único correo.
    """

    @swagger_auto_schema(
        operation_description="Reemplazar un instructor reasignando los contratos del instructor anterior al nuevo instructor.",
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
            
            instructor_anterior_id = request.data.get('instructor_anterior_id')
            nombre = request.data.get('nombre')
            apellido = request.data.get('apellido')
            email = request.data.get('email')
			

            instructor_anterior = Instructor.objects.get(id=instructor_anterior_id)

            nuevo_instructor = Instructor.objects.create(
                first_name=nombre,
                last_name=apellido,
                email=email,
											  
																		  
                empresa=instructor_anterior.empresa,
																					
																			  
                debeCambiarContraseña=True
            )

            
            temp_password = nuevo_instructor.generar_contraseña_temporal()

            
            contratos = Contrato.objects.filter(instructor=instructor_anterior)
            contratos.update(instructor=nuevo_instructor)

           
            contratos_por_codigo = {}
            for contrato in contratos:
                if contrato.codigoOrganizacion not in contratos_por_codigo:
                    contratos_por_codigo[contrato.codigoOrganizacion] = []
                contratos_por_codigo[contrato.codigoOrganizacion].append(contrato)
            
            cursos_info = ""
            for codigo, contratos in contratos_por_codigo.items():
                cursos_info += f"\nCódigo de organización: {codigo}\n"
                cursos_info += "\n".join([
                    f"- {contrato.curso.titulo} (Inicio: {contrato.fechaInicioCapacitacion}, Fin: {contrato.fechaFinCapacitacion})"
                    for contrato in contratos
                ])
                cursos_info += "\n"
            
            email_service = EmailService(
                to_email=nuevo_instructor.email,
                subject='Asignación de contratos',
                body=f"""
                Hola {nuevo_instructor.first_name},

                Usted ha sido asignado como instructor a los siguientes cursos:

                {cursos_info}

                Aquí están sus credenciales de acceso:
                - Correo electrónico: {nuevo_instructor.email}
                - Contraseña temporal: {temp_password}

                Por favor, cambie su contraseña después de iniciar sesión.

                Saludos,
                Global QHSE
                """
            )
            email_service.send_email()

            
            instructor_anterior.delete()

            return Response(
                {"message": f"Instructor {instructor_anterior.email} reemplazado por {nuevo_instructor.email}."},
                status=status.HTTP_200_OK
            )

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
                'codigoOrganizacion', 
                openapi.IN_QUERY,  
                description="Código de organización para filtrar estudiantes",
                type=openapi.TYPE_STRING,  
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
    basado en el codigoOrganizacion. Si el correo ya existe y es un estudiante, se actualiza el codigoOrganizacion.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Crear un estudiante y asignarlo automáticamente a los cursos de su instructor en base al codigoOrganizacion. Si el correo ya existe y es un estudiante, se actualiza el codigoOrganizacion.",
        request_body=EstudianteSerializer, 
        responses={
            201: openapi.Response(
                'Estudiante creado o actualizado con éxito',
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

        serializer = EstudianteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            email = serializer.validated_data['email']
            codigo_organizacion = serializer.validated_data['codigoOrganizacion']

            try:
                estudiante = Estudiante.objects.get(email=email)
                if estudiante.rol == 'estudiante':
                    
                    estudiante.codigoOrganizacion = codigo_organizacion
                    estudiante.save()
                    return Response(
                        {"message": f"Estudiante {email} actualizado con el nuevo código de organización {codigo_organizacion}."},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {"error": "El correo ingresado pertenece a un usuario que no es estudiante."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Estudiante.DoesNotExist:
               
                estudiante = Estudiante.crear_estudiante_con_cursos(
                    email=email,
                    password=serializer.validated_data['password'],
                    codigoOrganizacion=codigo_organizacion,
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', '')
                )
                return Response(
                    {"message": f"Estudiante {estudiante.email} creado exitosamente."},
                    status=status.HTTP_201_CREATED
                )

        except ValidationError as e:
            
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:

            logger.error(f"Error inesperado al registrar estudiante: {str(e)}")
            return Response(
                {"error": "Ocurrió un error inesperado. Por favor, intente más tarde."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            403: "Cuenta desactivada",
            403: "Sin contrato vigente",
        }
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        
        if user is not None:
			
            if user.is_active:
                hoy = date.today()
                
               
                if user.rol == 'estudiante':
                   
                    estudiante = Estudiante.objects.get(id=user.id)
                   
                    if not Contrato.objects.filter(
                        codigoOrganizacion=estudiante.codigoOrganizacion,
                        activo=True,
                        fechaInicioCapacitacion__lte=hoy,
                        fechaFinCapacitacion__gte=hoy
                    ).exists():
                        return Response({'error': 'No tiene contratos vigentes asociados.'}, status=status.HTTP_403_FORBIDDEN)
                    
                    serializer = EstudianteDetailSerializer(estudiante)
                
                elif user.rol == 'instructor':
                   
                    if not Contrato.objects.filter(
                        instructor=user,
                        activo=True,
                        fechaInicioCapacitacion__lte=hoy,
                        fechaFinCapacitacion__gte=hoy
                    ).exists():
                        return Response({'error': 'No tiene contratos vigentes asociados.'}, status=status.HTTP_403_FORBIDDEN)
                    
                    user = Instructor.objects.get(id=user.id) 
                    serializer = InstructorDetailSerializer(user)
                
                elif user.rol == 'admin':
                    user = Administrador.objects.get(id=user.id)  
                    serializer = AdministradorDetailSerializer(user)
                else:
                    return Response({'error': 'Rol no válido.'}, status=status.HTTP_400_BAD_REQUEST)

                refresh = RefreshToken.for_user(user)

                
                response_data = serializer.data
                response_data['refresh'] = str(refresh)
                response_data['access'] = str(refresh.access_token)

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
        user = request.user  
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'Ambos campos (old_password y new_password) son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

       
        if not user.check_password(old_password):
            return Response({'error': 'La contraseña antigua no es correcta.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.check_password(new_password):
            return Response({'error': 'La nueva contraseña no puede ser igual a la contraseña actual.'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        user.set_password(new_password)
        user.save()

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
       
        curso_anterior = self.get_object()

       
        instance = serializer.save()

        if not curso_anterior.simulacion and instance.simulacion:
            Progreso.objects.filter(
                curso=instance,
                fechaFinCurso__isnull=True,  
                porcentajeCompletado__lt=100,  
                simulacionCompletada__isnull=True  
            ).update(simulacionCompletada=False)

        
        elif curso_anterior.simulacion and not instance.simulacion:
           
            Progreso.objects.filter(
                curso=instance
            ).update(simulacionCompletada=None)
    @swagger_auto_schema(
        operation_description="Obtiene los cursos con simulación pendientes de completar para un estudiante.",
        manual_parameters=[
            openapi.Parameter(
                'estudiante_id',
                openapi.IN_QUERY,
                description="ID del estudiante para filtrar los cursos pendientes de simulación.",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Cursos pendientes de simulación",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del curso"),
                            'titulo': openapi.Schema(type=openapi.TYPE_STRING, description="Título del curso"),
                            'descripcion': openapi.Schema(type=openapi.TYPE_STRING, description="Descripción del curso"),
                            'simulacion': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Indica si el curso tiene simulación habilitada"),
                            'fecha_inicio': openapi.Schema(type=openapi.FORMAT_DATE, description="Fecha de inicio del curso"),
                            'fecha_fin': openapi.Schema(type=openapi.FORMAT_DATE, description="Fecha de fin del curso"),
                        }
                    )
                )
            ),
            400: openapi.Response(
                description="Error en los parámetros de la consulta",
                examples={
                    "application/json": {"error": "El parámetro 'estudiante_id' es requerido."}
                }
            )
        }
    )
    @action(detail=False, methods=['get'], url_path='pendientes-simulacion')
    def pendientes_simulacion(self, request):
        """
        Obtiene los cursos asociados a un estudiante que tienen simulación habilitada
        y donde el progreso no está marcado como completado.
        """
        estudiante_id = request.query_params.get('estudiante_id')
        if not estudiante_id:
            return Response(
                {"error": "El parámetro 'estudiante_id' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
 
       
        progresos = Progreso.objects.filter(
            estudiante_id=estudiante_id,
            simulacionCompletada=False,
            curso__simulacion=True  
        ).select_related('curso')
 
        
        cursos = {progreso.curso for progreso in progresos}
 
       
        serializer = self.get_serializer(cursos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

	
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
        
        serializer = ModuloSerializer(modulos, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DescargarArchivoModuloAPIView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request, pk, *args, **kwargs):
        try:
            
            modulo = Modulo.objects.get(pk=pk)

           
            if not modulo.archivo:
                return Response({"error": "Este módulo no tiene un archivo asociado."}, status=status.HTTP_404_NOT_FOUND)

           
            archivo = modulo.archivo.path
            response = FileResponse(open(archivo, 'rb'), content_type='application/octet-stream')
            response['Content-Disposition'] = f'inline; filename="{modulo.archivo.name}"'
            return response

        except Modulo.DoesNotExist:
            raise Http404("Módulo no encontrado.")
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            


class ContratoAPIView(APIView):
    """
    API para gestionar las relaciones entre instructores y cursos.
    """

    @swagger_auto_schema(
        operation_description="Obtiene todas las relaciones entre instructores y cursos o filtra por instructor y curso.",
        manual_parameters=[
            openapi.Parameter('instructor', openapi.IN_QUERY, description="ID del instructor", type=openapi.TYPE_INTEGER),
            openapi.Parameter('curso', openapi.IN_QUERY, description="ID del curso", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ContratoSerializer(many=True)}
    )
    def get(self, request):
        instructor_id = request.query_params.get('instructor')
        curso_id = request.query_params.get('curso')

        
        if instructor_id and curso_id:
            relaciones = Contrato.objects.filter(instructor_id=instructor_id, curso_id=curso_id)
        elif instructor_id:
            relaciones = Contrato.objects.filter(instructor_id=instructor_id)
        elif curso_id:
            relaciones = Contrato.objects.filter(curso_id=curso_id)
        else:
            relaciones = Contrato.objects.all()

        serializer = ContratoSerializer(relaciones, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Crea una nueva relación entre un instructor y un curso.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'instructor': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del instructor'),
                'curso': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
                'codigoOrganizacion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Código de organización asociado al contrato. (Opcional: Si no se proporciona, se generará uno nuevo automáticamente)'
                )
            },
            required=['instructor', 'curso']
        ),
        responses={
            201: openapi.Response(
                'Relación creada exitosamente.',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Mensaje de éxito'),
                    }
                )
            ),
            400: 'Error en los datos enviados.',
            500: 'Error interno del servidor.',
        }
    )

    def post(self, request):
        instructor_id = request.data.get('instructor')
        curso_id = request.data.get('curso')
        codigo_organizacion = request.data.get('codigoOrganizacion') 

        if not instructor_id or not curso_id:
            return Response({"error": "Los campos 'instructor' y 'curso' son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                
                if not codigo_organizacion:
                    
                    instructor = get_object_or_404(Instructor, id=instructor_id)
                    prefix = instructor.empresa.nombre[:3].upper()
                    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    codigo_organizacion = f"{prefix}-{suffix}"

                
                relacion = Contrato.objects.create(
                    instructor_id=instructor_id,
                    curso_id=curso_id,
                    codigoOrganizacion=codigo_organizacion
                )

                
                estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)

                
                progreso_records = []
                estudiante_prueba_records = []
                estudiante_subcurso_records = []
                estudiante_modulo_records = []

                for estudiante in estudiantes:
                    progreso_records.append(
                        Progreso(estudiante=estudiante, curso_id=curso_id, completado=False, porcentajeCompletado=0)
                    )
			  

                    pruebas = Prueba.objects.filter(curso_id=curso_id)
                    for prueba in pruebas:
                        estudiante_prueba_records.append(
                            EstudiantePrueba(estudiante=estudiante, prueba=prueba)
                        )

                    subcursos = Subcurso.objects.filter(curso_id=curso_id)
                    for subcurso in subcursos:
                        estudiante_subcurso_records.append(
                            EstudianteSubcurso(estudiante=estudiante, subcurso=subcurso, completado=False, porcentajeCompletado=0.0)
                        )

                        modulos = Modulo.objects.filter(subcurso=subcurso)
                        for modulo in modulos:
                            estudiante_modulo_records.append(
                                EstudianteModulo(estudiante=estudiante, modulo=modulo, completado=False)
                            )

                Progreso.objects.bulk_create(progreso_records)
                EstudiantePrueba.objects.bulk_create(estudiante_prueba_records)
                EstudianteSubcurso.objects.bulk_create(estudiante_subcurso_records)
                EstudianteModulo.objects.bulk_create(estudiante_modulo_records)

            return Response({"message": "Relación creada exitosamente."}, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"error": "La relación entre el instructor y el curso ya existe."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="Elimina una relación entre un instructor, un curso, y un código de organización.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'codigoOrganizacion': openapi.Schema(type=openapi.TYPE_STRING, description='Código de organización del contrato'),
                'instructor': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del instructor'),
                'curso': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID del curso'),
            },
            required=['codigoOrganizacion', 'instructor', 'curso']
        ),
        responses={
            200: openapi.Response('Relación eliminada exitosamente.'),
            400: 'Error en los datos enviados.',
            404: 'Relación no encontrada.',
        }
    )
    def delete(self, request):
        codigo_organizacion = request.data.get('codigoOrganizacion')
        instructor_id = request.data.get('instructor')
        curso_id = request.data.get('curso')

        
        if not codigo_organizacion or not instructor_id or not curso_id:
            return Response(
                {"error": "Los campos 'codigoOrganizacion', 'instructor', y 'curso' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                
                relacion = Contrato.objects.get(
                    codigoOrganizacion=codigo_organizacion,
                    instructor_id=instructor_id,
                    curso_id=curso_id
                )
																		

                
                estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)

               
                Progreso.objects.filter(estudiante__in=estudiantes, curso_id=curso_id).delete()
                pruebas = Prueba.objects.filter(curso_id=curso_id)
                EstudiantePrueba.objects.filter(estudiante__in=estudiantes, prueba__in=pruebas).delete()
                subcursos = Subcurso.objects.filter(curso_id=curso_id)
                EstudianteSubcurso.objects.filter(estudiante__in=estudiantes, subcurso__in=subcursos).delete()
                modulos = Modulo.objects.filter(subcurso__in=subcursos)
                EstudianteModulo.objects.filter(estudiante__in=estudiantes, modulo__in=modulos).delete()

               
                relacion.delete()

            return Response({"message": "Relación eliminada exitosamente."}, status=status.HTTP_200_OK)
        except Contrato.DoesNotExist:
            return Response(
                {"error": "La relación entre el instructor, el curso, y el código de organización no fue encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
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
 
 
        if not codigo_organizacion:
            return Response(
                {"error": "El parámetro 'codigoOrganizacion' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

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
        estudiante_id = self.request.query_params.get('estudiante_id')  
        if estudiante_id:
            return Progreso.objects.filter(estudiante_id=estudiante_id)
        return super().get_queryset()  
   
    @swagger_auto_schema(
        operation_description="Actualiza el campo `simulacionCompletada` de un registro de progreso basado en `estudiante_id` y `curso_id`.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del estudiante"),
                'curso_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del curso"),
                'simulacionCompletada': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Estado de simulación completada"),
            },
            required=['estudiante_id', 'curso_id', 'simulacionCompletada']
        ),
        responses={
            200: ProgresoSerializer,
            400: "Error en los datos enviados",
            404: "Registro de progreso no encontrado",
        }
    )
    @action(detail=False, methods=['patch'], url_path='actualizar-simulacion')
    def actualizar_simulacion(self, request):
        """
        Actualiza el campo `simulacionCompletada` para un estudiante en un curso específico.
        """
        estudiante_id = request.data.get('estudiante_id')
        curso_id = request.data.get('curso_id')
        simulacion_completada = request.data.get('simulacionCompletada')

        if not estudiante_id or not curso_id or simulacion_completada is None:
            return Response(
                {"error": "Los campos `estudiante_id`, `curso_id` y `simulacionCompletada` son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            progreso = Progreso.objects.get(estudiante_id=estudiante_id, curso_id=curso_id)
        except Progreso.DoesNotExist:
            return Response(
                {"error": "No se encontró el registro de progreso para el estudiante y curso especificados."},
                status=status.HTTP_404_NOT_FOUND
            )

        progreso.simulacionCompletada = simulacion_completada
        progreso.save()
        serializer = ProgresoSerializer(progreso)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='verificar-contrato-activo')
    def verificar_contrato_activo(self, request):
        """
        Verifica si un curso tiene un contrato activo.
        """
        curso_id = request.query_params.get('curso_id')

        if not curso_id:
            return Response(
                {"error": "El parámetro `curso_id` es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar si el curso tiene un contrato activo
        hoy = now().date()
        contrato_activo = Contrato.objects.filter(
            curso_id=curso_id,
            activo=True,
            fechaInicioCapacitacion__lte=hoy,
            fechaFinCapacitacion__gte=hoy
        ).exists()

        return Response(
            {
                "curso_id": curso_id,
                "activo": contrato_activo
            },
            status=status.HTTP_200_OK
        )


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

        
        if not estudiante_id or not curso_id:
            return Response({"error": "Los campos 'estudiante_id' y 'curso_id' son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

       
        try:
            estudiante = Estudiante.objects.get(id=estudiante_id)
            curso = Curso.objects.get(id=curso_id)
        except Estudiante.DoesNotExist:
            return Response({"error": "Estudiante no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Curso.DoesNotExist:
            return Response({"error": "Curso no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        
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
            prueba = self.get_object()  
            preguntas_data = request.data  

            if not isinstance(preguntas_data, list):
                return Response(
                    {"error": "El cuerpo de la solicitud debe ser una lista de preguntas."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            for pregunta_data in preguntas_data:
                pregunta_data['prueba'] = prueba.id  
                serializer = PreguntaSerializer(data=pregunta_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            return Response({"message": "Preguntas agregadas con éxito."}, status=status.HTTP_201_CREATED)

        except Prueba.DoesNotExist:
            return Response({"error": "Prueba no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @swagger_auto_schema(
        operation_description="Verifica si un curso tiene una prueba asociada.",
        manual_parameters=[
            openapi.Parameter(
                'curso_id',
                openapi.IN_QUERY,
                description="ID del curso para verificar si tiene una prueba asociada.",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                "Estado de la prueba para el curso",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "curso_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del curso"),
                        "tiene_prueba": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Indica si el curso tiene una prueba asociada"),
                    }
                )
            ),
            400: "El parámetro `curso_id` es requerido.",
        }
    )
    @action(detail=False, methods=['get'], url_path='verificar-prueba')
    def verificar_prueba(self, request):
        """
        Verifica si un curso tiene una prueba asociada.
        """
        curso_id = request.query_params.get('curso_id')

        if not curso_id:
            return Response(
                {"error": "El parámetro `curso_id` es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        tiene_prueba = Prueba.objects.filter(curso_id=curso_id).exists()

        return Response(
            {
                "curso_id": int(curso_id),
                "tiene_prueba": tiene_prueba
            },
            status=status.HTTP_200_OK
        )

class PreguntaViewSet(viewsets.ModelViewSet):
    queryset = Pregunta.objects.all()
    serializer_class = PreguntaSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['prueba']  #

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list): 
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

        curso_id = request.query_params.get('curso_id')
        estudiante_id = request.query_params.get('estudiante_id')

        if not curso_id or not estudiante_id:
            return Response(
                {"error": "Se requieren los parámetros 'curso_id' y 'estudiante_id'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            certificado = Certificado.objects.get(curso_id=curso_id, estudiante_id=estudiante_id)
        except Certificado.DoesNotExist:
            return Response(
                {"error": "No se encontró un certificado para el curso y estudiante especificados."},
                status=status.HTTP_404_NOT_FOUND
            )

       
        if not certificado.archivoPdf:
            return Response(
                {"error": "El certificado no tiene un archivo PDF asociado."},
                status=status.HTTP_404_NOT_FOUND
            )

       
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
    """
    API para actualizar los campos de un registro de EstudiantePrueba.
    """
    @swagger_auto_schema(
        operation_description="Actualizar los campos de un registro de EstudiantePrueba basado en estudiante_id y prueba_id.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estudiante_id', 'prueba_id'],
            properties={
                'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del estudiante"),
                'prueba_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID de la prueba"),
                'estaAprobado': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Estado de aprobación del estudiante (opcional)"),
                'calificacion': openapi.Schema(type=openapi.TYPE_NUMBER, description="Calificación obtenida por el estudiante (opcional)")
               
            }
        ),
        responses={
            200: openapi.Response(
                description="Registro actualizado correctamente.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'estaAprobado': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Estado de aprobación del estudiante"),
                        'calificacion': openapi.Schema(type=openapi.TYPE_NUMBER, description="Calificación obtenida"),
                        'intento': openapi.Schema(type=openapi.TYPE_INTEGER, description="Número de intentos realizados"),
                        'fechaPrueba': openapi.Schema(type=openapi.TYPE_STRING, format="date", description="Fecha de la prueba")
                    }
                )
            ),
            400: openapi.Response(description="Error en la solicitud."),
            404: openapi.Response(description="Registro no encontrado.")
        }
    )
    def patch(self, request):
        estudiante_id = request.data.get('estudiante_id')
        prueba_id = request.data.get('prueba_id')
 
        if not estudiante_id or not prueba_id:
            return Response({"error": "Los campos 'estudiante_id' y 'prueba_id' son requeridos."}, status=status.HTTP_400_BAD_REQUEST)
 
        estudiante_prueba = get_object_or_404(EstudiantePrueba, estudiante_id=estudiante_id, prueba_id=prueba_id)
 
        estudiante_prueba.intento += 1
        estudiante_prueba.fechaPrueba = date.today()
 
        serializer = EstudiantePruebaSerializer(estudiante_prueba, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()  
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PruebasEstudianteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        estudiante_id = request.user.id  
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

        preguntas = Pregunta.objects.filter(prueba_id=prueba_id)
        calificacion_total = 0
        puntos_por_pregunta = preguntas.first().puntajePregunta 
        for pregunta in preguntas:
            respuesta_correcta = pregunta.respuestaCorrecta
            respuesta_del_estudiante = respuestas.get(str(pregunta.id))  

            if respuesta_del_estudiante and respuesta_del_estudiante.lower() == respuesta_correcta.lower():
                calificacion_total += puntos_por_pregunta

       
        estudiante_prueba.calificacion = calificacion_total
        estudiante_prueba.estaAprobado = calificacion_total >= 60 
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

        
        estudiante_prueba = EstudiantePrueba.objects.filter(
            prueba_id=prueba_id, estudiante_id=estudiante_id
        ).first()

        if not estudiante_prueba:
            return Response(
                {"error": "La prueba no está asignada a este estudiante o no existe."},
                status=404
            )

        
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
class CrearContratosAPIView(APIView):
    """
    API para crear múltiples contratos y enviar un correo único basado en el `codigoOrganizacion`.
    """
    @swagger_auto_schema(
        operation_description="Crea múltiples contratos y envía un correo único basado en el código de organización.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'contratos': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'instructor': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del instructor"),
                            'curso': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del curso"),
                            'fechaInicioCapacitacion': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                format=openapi.FORMAT_DATE,
                                description="Fecha de inicio de la capacitación"
                            ),
                            'fechaFinCapacitacion': openapi.Schema(
                                type=openapi.TYPE_STRING,
                                format=openapi.FORMAT_DATE,
                                description="Fecha de fin de la capacitación"
                            ),
                        },
                        required=['instructor', 'curso', 'fechaInicioCapacitacion', 'fechaFinCapacitacion']
                    ),
                    description="Lista de contratos a crear"
                )
            },
            required=['contratos']
        ),
        responses={
            201: openapi.Response("Contratos creados exitosamente."),
            400: openapi.Response("Error en los datos enviados."),
            500: openapi.Response("Error interno del servidor."),
        }
    )
    def post(self, request):
        contratos_data = request.data.get('contratos', [])
        if not contratos_data:
            return Response({"error": "Se requiere una lista de contratos."}, status=status.HTTP_400_BAD_REQUEST)
 
        try:
            with transaction.atomic():
                contratos_creados = []
                codigo_organizacion = None
                instructor = None
 
                for idx, contrato_data in enumerate(contratos_data):
                    serializer = ContratoSerializer(data=contrato_data)
                    if serializer.is_valid():
                        contrato = serializer.save()
 
                        
                        if codigo_organizacion:
                            contrato.set_force_codigo(codigo_organizacion)
                            contrato.save()
                        else:  
                            codigo_organizacion = contrato.codigoOrganizacion
                            instructor = contrato.instructor
 
                        contratos_creados.append(contrato)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
                if contratos_creados and instructor:
                    cursos_info = "\n".join([
                        f"- {contrato.curso.titulo} (Inicio: {contrato.fechaInicioCapacitacion}, Fin: {contrato.fechaFinCapacitacion})"
                        for contrato in contratos_creados
                    ])
                    email_service = EmailService(
                        to_email=instructor.email,
                        subject='Asignación de cursos',
                        body=f"""
                        Hola {instructor.first_name},
 
                        Usted ha sido asignado como instructor a los siguientes cursos bajo el código de organización {codigo_organizacion}:
 
                        {cursos_info}
 
                        Por favor comparta el código de organización con sus estudiantes para su registro y acceda al sistema para revisar los detalles del progreso de los estudiantes.
 
                        Saludos,
                        Equipo de Global QHSE
                        """
                    )
                    email_service.send_email()
 
                return Response({"message": "Contratos creados exitosamente."}, status=status.HTTP_201_CREATED)
 
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.error(f"Error inesperado en CrearContratosAPIView: {traceback_str}")
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ObtenerContratosAPIView(APIView):
    """
    API para obtener todos los contratos asociados a un `codigoOrganizacion`.
    """
    @swagger_auto_schema(
        operation_description="Obtiene todos los contratos asociados a un código de organización.",
        manual_parameters=[
            openapi.Parameter('codigoOrganizacion', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True,
                              description="Código de organización para filtrar los contratos")
        ],
        responses={
            200: ContratoSerializer(many=True),
            400: "El parámetro 'codigoOrganizacion' es requerido.",
        }
    )
    def get(self, request):
        codigo_organizacion = request.query_params.get('codigoOrganizacion')

        if not codigo_organizacion:
            return Response({"error": "El parámetro 'codigoOrganizacion' es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        contratos = Contrato.objects.filter(codigoOrganizacion=codigo_organizacion)
        serializer = ContratoSerializer(contratos, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
class ActualizarContratosAPIView(APIView):
    """
    API para actualizar múltiples contratos asociados a un `codigoOrganizacion`.
    """
    @swagger_auto_schema(
        operation_description="Actualiza todos los contratos asociados a un código de organización.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'codigoOrganizacion': openapi.Schema(type=openapi.TYPE_STRING, description="Código de organización"),
                'fechaInicioCapacitacion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATE,
                    description="Nueva fecha de inicio de capacitación (opcional)"
                ),
                'fechaFinCapacitacion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_DATE,
                    description="Nueva fecha de fin de capacitación (opcional)"
                ),
                'activo': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Estado del contrato (opcional)"),
            },
            required=['codigoOrganizacion']
        ),
        responses={
            200: "Contratos actualizados exitosamente.",
            400: "Error en los datos enviados.",
            500: "Error interno del servidor.",
										 
        }
    )
    def patch(self, request):
        codigo_organizacion = request.data.get('codigoOrganizacion')
        fecha_inicio = request.data.get('fechaInicioCapacitacion')
        fecha_fin = request.data.get('fechaFinCapacitacion')
        activo = request.data.get('activo')

        if not codigo_organizacion:
            return Response({"error": "El campo 'codigoOrganizacion' es requerido."}, status=status.HTTP_400_BAD_REQUEST)
																	  

        try:
            with transaction.atomic():
                contratos = Contrato.objects.filter(codigoOrganizacion=codigo_organizacion)

                if not contratos.exists():
                    return Response(
                        {"error": "No se encontraron contratos con el código de organización especificado."},
                        status=status.HTTP_404_NOT_FOUND
                    )

                
                cursos_ids = contratos.values_list('curso_id', flat=True)
                estudiantes = Estudiante.objects.filter(codigoOrganizacion=codigo_organizacion)

                for contrato in contratos:
                    if fecha_inicio:
                        contrato.fechaInicioCapacitacion = fecha_inicio
                    if fecha_fin:
                        contrato.fechaFinCapacitacion = fecha_fin
                    if activo is not None:
                        contrato.activo = activo
                        if not activo:  
                            Progreso.objects.filter(estudiante__in=estudiantes, curso_id__in=cursos_ids).delete()
                            pruebas = Prueba.objects.filter(curso_id__in=cursos_ids)
                            EstudiantePrueba.objects.filter(estudiante__in=estudiantes, prueba__in=pruebas).delete()
                            subcursos = Subcurso.objects.filter(curso_id__in=cursos_ids)
                            EstudianteSubcurso.objects.filter(estudiante__in=estudiantes, subcurso__in=subcursos).delete()
                            modulos = Modulo.objects.filter(subcurso__in=subcursos)
                            EstudianteModulo.objects.filter(estudiante__in=estudiantes, modulo__in=modulos).delete()
                    contrato.save()

                return Response({"message": "Contratos actualizados exitosamente."}, status=status.HTTP_200_OK)
														   
																							  
								

        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.error(f"Error inesperado en ActualizarContratoAPIView: {traceback_str}")
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
														   
														


class ContratosPorInstructorAPIView(APIView):
    """
    API para obtener todos los contratos asociados al ID del instructor, agrupados por código de organización.
    """
    @swagger_auto_schema(
        operation_description="Obtiene todos los contratos asociados al ID de un instructor, agrupados por código de organización.",
        manual_parameters=[
            openapi.Parameter(
                'instructor_id',
                openapi.IN_QUERY,
                description="ID del instructor",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response("Contratos agrupados por código de organización."),
            400: "Error en los datos enviados."
											 
			  
																	
        }
    )
    def get(self, request):
        instructor_id = request.query_params.get('instructor_id')
									   

        if not instructor_id:
            return Response({"error": "El campo 'instructor_id' es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
           
            contratos = Contrato.objects.filter(instructor_id=instructor_id)
				 
            if not contratos.exists():
                return Response({}, status=status.HTTP_200_OK)
						  
            agrupados_por_codigo = {}
            for contrato in contratos:
                codigo = contrato.codigoOrganizacion
                if codigo not in agrupados_por_codigo:
                    agrupados_por_codigo[codigo] = []
                agrupados_por_codigo[codigo].append({
                    "curso_id": contrato.curso.id,
                    "curso_titulo": contrato.curso.titulo,
                    "fechaInicioCapacitacion": contrato.fechaInicioCapacitacion,
                    "fechaFinCapacitacion": contrato.fechaFinCapacitacion,
                    "activo": contrato.activo if hasattr(contrato, 'activo') else None
                })

            return Response(agrupados_por_codigo, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Ocurrió un error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#METRICAS
 
 
 
class GeneralMetricsAPIView(APIView):
    def get(self, request):
        from django.utils.timezone import now
        from django.db.models import Q
 
        empresa_id = request.query_params.get('empresa_id')
        curso_id = request.query_params.get('curso_id')
        fecha_actual = now().date()
 
        
        contrato_filter = Q()
        if empresa_id:
            contrato_filter &= Q(instructor__empresa_id=empresa_id)
        if curso_id:
            contrato_filter &= Q(curso__id=curso_id)
 
       
        contratos_filtrados = Contrato.objects.filter(contrato_filter).distinct()
 
       
        cursos_filtrados_ids = contratos_filtrados.values_list('curso_id', flat=True)
        codigos_org_filtrados = contratos_filtrados.values_list('codigoOrganizacion', flat=True)
 
        
        total_estudiantes = Estudiante.objects.filter(codigoOrganizacion__in=codigos_org_filtrados).distinct().count()
 
       
        if empresa_id:
            total_instructores = Instructor.objects.filter(empresa_id=empresa_id).count()
        else:
            total_instructores = Instructor.objects.count()
 
       
        total_empresas = Empresa.objects.count()
        total_cursos = Curso.objects.count()
 
        
        total_certificados = Certificado.objects.filter(
            Q(curso_id__in=cursos_filtrados_ids) |
            Q(estudiante__codigoOrganizacion__in=codigos_org_filtrados)
        ).count()
 
       
        total_pruebas = EstudiantePrueba.objects.filter(
            prueba__curso_id__in=cursos_filtrados_ids
        ).count()
 
        pruebas_aprobadas = EstudiantePrueba.objects.filter(
            estaAprobado=True,
            prueba__curso_id__in=cursos_filtrados_ids
        ).count()
 
       
        instructores_activos_qs = Instructor.objects.filter(
            cursos_asignados__fechaInicioCapacitacion__lte=fecha_actual,
            cursos_asignados__fechaFinCapacitacion__gte=fecha_actual
        )
        if empresa_id:
            instructores_activos_qs = instructores_activos_qs.filter(empresa_id=empresa_id)
        if curso_id:
            instructores_activos_qs = instructores_activos_qs.filter(
                cursos_asignados__curso_id=curso_id
            )
        instructores_activos = instructores_activos_qs.distinct().count()
 
       
        contratos_activos_filtrados = contratos_filtrados.filter(
            fechaInicioCapacitacion__lte=fecha_actual,
            fechaFinCapacitacion__gte=fecha_actual
        )
        codigos_activos = contratos_activos_filtrados.values_list('codigoOrganizacion', flat=True)
        estudiantes_activos = Estudiante.objects.filter(
            codigoOrganizacion__in=codigos_activos
        ).distinct().count()
 
        
        tasa_certificacion = (
            (total_certificados / total_estudiantes) * 100 if total_estudiantes > 0 else 0
        )
        tasa_aprobacion = (
            (pruebas_aprobadas / total_pruebas) * 100 if total_pruebas > 0 else 0
        )
 
        data = {
            "total_estudiantes": total_estudiantes,
            "total_instructores": total_instructores,
            "total_empresas": total_empresas,
            "total_cursos": total_cursos,
            "total_certificados": total_certificados,
            "tasa_certificacion": round(tasa_certificacion, 2),
            "total_pruebas": total_pruebas,
            "pruebas_aprobadas": pruebas_aprobadas,
            "tasa_aprobacion": round(tasa_aprobacion, 2),
            "instructores_activos": instructores_activos,
            "estudiantes_activos": estudiantes_activos,
        }
        return Response(data)
 
class InstructorGeneralMetricsAPIView(APIView):
    """
    API para obtener métricas de UN instructor vs. las métricas generales de su empresa.
    Recibe como parámetro: ?instructor_id=123
    """
    def get(self, request):
        
        instructor_id = request.query_params.get('instructor_id', None)
        if not instructor_id:
            return Response({"error": "Debes proporcionar ?instructor_id="}, status=400)
       
        
        instructor = get_object_or_404(Instructor, id=instructor_id)
       
        
        empresa = instructor.empresa
        fecha_actual = now().date()
       
        
        contratos_instructor = Contrato.objects.filter(instructor=instructor).distinct()
       
        cursos_instructor_ids = contratos_instructor.values_list('curso_id', flat=True)
        codigos_org_instructor = contratos_instructor.values_list('codigoOrganizacion', flat=True)
       
        total_estudiantes_instructor = Estudiante.objects.filter(
            codigoOrganizacion__in=codigos_org_instructor
        ).distinct().count()
       
        total_certificados_instructor = Certificado.objects.filter(
            Q(curso_id__in=cursos_instructor_ids) |
            Q(estudiante__codigoOrganizacion__in=codigos_org_instructor)
        ).count()
       
        total_pruebas_instructor = EstudiantePrueba.objects.filter(
            prueba__curso_id__in=cursos_instructor_ids
        ).count()
       
        pruebas_aprobadas_instructor = EstudiantePrueba.objects.filter(
            estaAprobado=True,
            prueba__curso_id__in=cursos_instructor_ids
        ).count()
       
       
        contratos_activos_instructor = contratos_instructor.filter(
            fechaInicioCapacitacion__lte=fecha_actual,
            fechaFinCapacitacion__gte=fecha_actual
        )
        codigos_activos_instructor = contratos_activos_instructor.values_list('codigoOrganizacion', flat=True)
        estudiantes_activos_instructor = Estudiante.objects.filter(
            codigoOrganizacion__in=codigos_activos_instructor
        ).distinct().count()
       
        
        tasa_certificacion_instructor = (
            (total_certificados_instructor / total_estudiantes_instructor) * 100
            if total_estudiantes_instructor > 0 else 0
        )
        tasa_aprobacion_instructor = (
            (pruebas_aprobadas_instructor / total_pruebas_instructor) * 100
            if total_pruebas_instructor > 0 else 0
        )
       
        
        contratos_empresa = Contrato.objects.filter(instructor__empresa=empresa).distinct()
       
        cursos_empresa_ids = contratos_empresa.values_list('curso_id', flat=True)
        codigos_org_empresa = contratos_empresa.values_list('codigoOrganizacion', flat=True)
       
        total_estudiantes_empresa = Estudiante.objects.filter(
            codigoOrganizacion__in=codigos_org_empresa
        ).distinct().count()
       
        total_instructores_empresa = Instructor.objects.filter(empresa=empresa).count()
       
        total_certificados_empresa = Certificado.objects.filter(
            Q(curso_id__in=cursos_empresa_ids) |
            Q(estudiante__codigoOrganizacion__in=codigos_org_empresa)
        ).count()
       
        total_pruebas_empresa = EstudiantePrueba.objects.filter(
            prueba__curso_id__in=cursos_empresa_ids
        ).count()
       
        pruebas_aprobadas_empresa = EstudiantePrueba.objects.filter(
            estaAprobado=True,
            prueba__curso_id__in=cursos_empresa_ids
        ).count()
       
        contratos_activos_empresa = contratos_empresa.filter(
            fechaInicioCapacitacion__lte=fecha_actual,
            fechaFinCapacitacion__gte=fecha_actual
        )
        codigos_activos_empresa = contratos_activos_empresa.values_list('codigoOrganizacion', flat=True)
        estudiantes_activos_empresa = Estudiante.objects.filter(
            codigoOrganizacion__in=codigos_activos_empresa
        ).distinct().count()
       
        tasa_certificacion_empresa = (
            (total_certificados_empresa / total_estudiantes_empresa) * 100
            if total_estudiantes_empresa > 0 else 0
        )
        tasa_aprobacion_empresa = (
            (pruebas_aprobadas_empresa / total_pruebas_empresa) * 100
            if total_pruebas_empresa > 0 else 0
        )
       
       
        total_cursos_empresa = Curso.objects.filter(id__in=cursos_empresa_ids).count()
 
        data = {
            "instructor_metrics": {
                "instructor_id": instructor_id,
                "instructor_email": instructor.email,
                "empresa_id": empresa.id,
                "empresa_nombre": empresa.nombre,
                "total_estudiantes": total_estudiantes_instructor,
                "total_certificados": total_certificados_instructor,
                "total_pruebas": total_pruebas_instructor,
                "pruebas_aprobadas": pruebas_aprobadas_instructor,
                "estudiantes_activos": estudiantes_activos_instructor,
                "tasa_certificacion": round(tasa_certificacion_instructor, 2),
                "tasa_aprobacion": round(tasa_aprobacion_instructor, 2),
            },
            "empresa_metrics": {
                "nombre_empresa": empresa.nombre,
                "total_instructores": total_instructores_empresa,
                "total_estudiantes": total_estudiantes_empresa,
                "total_certificados": total_certificados_empresa,
                "total_pruebas": total_pruebas_empresa,
                "pruebas_aprobadas": pruebas_aprobadas_empresa,
                "estudiantes_activos": estudiantes_activos_empresa,
                "tasa_certificacion": round(tasa_certificacion_empresa, 2),
                "tasa_aprobacion": round(tasa_aprobacion_empresa, 2),
                "total_cursos": total_cursos_empresa,
            }
        }
       
        return Response(data, status=status.HTTP_200_OK)
 
class InstructorCursosTasaFinalizacionAPIView(APIView):
    """
    API para ver la tasa de finalización de los cursos de UN instructor
    vs. la de todos los cursos de la misma empresa.
    Recibe como parámetro: ?instructor_id=123
    """
    def get(self, request):
        
        instructor_id = request.query_params.get('instructor_id', None)
        if not instructor_id:
            return Response({"error": "Debes proporcionar ?instructor_id="}, status=400)
       
        instructor = get_object_or_404(Instructor, id=instructor_id)
        empresa = instructor.empresa
       
        
        cursos_instructor_qs = Curso.objects.filter(
            instructores_asignados__instructor=instructor
        ).distinct()
       
        
        cursos_instructor_qs = cursos_instructor_qs.annotate(
            tasa_finalizacion=Avg('progresos__porcentajeCompletado')
        )
       
       
        curso_instructor_mayor = None
        curso_instructor_menor = None
        if cursos_instructor_qs.exists():
            curso_instructor_mayor = cursos_instructor_qs.order_by('-tasa_finalizacion').first()
            curso_instructor_menor = cursos_instructor_qs.order_by('tasa_finalizacion').first()

        cursos_empresa_qs = Curso.objects.filter(
            instructores_asignados__instructor__empresa=empresa
        ).distinct().annotate(
            tasa_finalizacion=Avg('progresos__porcentajeCompletado')
        )
       
        curso_empresa_mayor = None
        curso_empresa_menor = None
        if cursos_empresa_qs.exists():
            curso_empresa_mayor = cursos_empresa_qs.order_by('-tasa_finalizacion').first()
            curso_empresa_menor = cursos_empresa_qs.order_by('tasa_finalizacion').first()
       

        def info_curso(curso):
            if not curso or curso.tasa_finalizacion is None:
                return None
            return {
                "curso_id": curso.id,
                "titulo": curso.titulo,
                "tasa_finalizacion": round(curso.tasa_finalizacion, 2),
            }
       
        data = {
            "cursos_instructor": {
                "curso_mayor_finalizacion": info_curso(curso_instructor_mayor),
                "curso_menor_finalizacion": info_curso(curso_instructor_menor),
            },
            "cursos_empresa": {
                "curso_mayor_finalizacion": info_curso(curso_empresa_mayor),
                "curso_menor_finalizacion": info_curso(curso_empresa_menor),
            }
        }
       
        return Response(data, status=status.HTTP_200_OK)
 
class FilteredMetricsAPIView(APIView):
    """
    API para métricas con filtros.
    """
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id', None)
        curso_id = request.query_params.get('curso_id', None)
 
   
        empresa_filter = Q()
        curso_filter = Q()
 
        if empresa_id:
            empresa_filter &= Q(id=empresa_id)
 
        if curso_id:
            curso_filter &= Q(id=curso_id)
 
        
        total_estudiantes = Estudiante.objects.filter(empresa_filter).count()
        total_certificados = Certificado.objects.filter(curso__in=Curso.objects.filter(empresa_filter & curso_filter)).count()
 
        
        total_pruebas = EstudiantePrueba.objects.filter(prueba__curso__in=Curso.objects.filter(empresa_filter & curso_filter)).count()
        pruebas_aprobadas = EstudiantePrueba.objects.filter(estaAprobado=True, prueba__curso__in=Curso.objects.filter(empresa_filter & curso_filter)).count()
 
      
        tasa_certificacion = (
            (total_certificados / total_estudiantes) * 100 if total_estudiantes > 0 else 0
        )
        tasa_aprobacion = (
            (pruebas_aprobadas / total_pruebas) * 100 if total_pruebas > 0 else 0
        )
 
        data = {
            "total_estudiantes": total_estudiantes,
            "total_certificados": total_certificados,
            "tasa_certificacion": round(tasa_certificacion, 2),
            "total_pruebas": total_pruebas,
            "pruebas_aprobadas": pruebas_aprobadas,
            "tasa_aprobacion": round(tasa_aprobacion, 2),
        }
        return Response(data)
 

 
class EmpresasTotalesAPIView(APIView):
 
    authentication_classes = [JWTAuthentication]
   
    permission_classes = [IsAdminUser]
    """
    API para obtener el número total de empresas registradas.
    """
    def get(self, request):
        total_empresas = Empresa.objects.count()
        return Response({"total_empresas": total_empresas}, status=status.HTTP_200_OK)
 
 
class UsuariosTotalesAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
 
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
 
        if empresa_id:
           
            empresa = get_object_or_404(Empresa, id=empresa_id)
 
           
            instructores = Instructor.objects.filter(empresa_id=empresa_id)
            total_instructores = instructores.count()
 
            
            codigos_organizacion = Contrato.objects.filter(
                instructor__empresa_id=empresa_id
            ).values_list('codigoOrganizacion', flat=True).distinct()
 
            total_estudiantes = Estudiante.objects.filter(
                codigoOrganizacion__in=codigos_organizacion
            ).count()
        else:
            
            total_instructores = Instructor.objects.count()
            total_estudiantes = Estudiante.objects.count()
 
        return Response({
            "total_instructores": total_instructores,
            "total_estudiantes": total_estudiantes
        }, status=status.HTTP_200_OK)
 
   
class CursosTotalesAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    """
    API para obtener el número total de cursos registrados, con opción de filtrar por empresa.
    """
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
       
        if empresa_id:
            empresa = get_object_or_404(Empresa, id=empresa_id)
            instructores = Instructor.objects.filter(empresa_id=empresa_id).values_list('id', flat=True)
            total_cursos = Curso.objects.filter(instructores_asignados__instructor_id__in=instructores).distinct().count()
        else:
            total_cursos = Curso.objects.count()
        return Response({"total_cursos": total_cursos}, status=status.HTTP_200_OK)
   
class ProgresoPromedioAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
 
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        curso_id = request.query_params.get('curso_id')
 
        progresos = Progreso.objects.all()
 
      
        if empresa_id:
           
            empresa = get_object_or_404(Empresa, id=empresa_id)
 
           
            codigos_organizacion = Contrato.objects.filter(
                instructor__empresa_id=empresa_id
            ).values_list('codigoOrganizacion', flat=True).distinct()
 
           
            progresos = progresos.filter(estudiante__codigoOrganizacion__in=codigos_organizacion)
 
       
        if curso_id:
           
            get_object_or_404(Curso, id=curso_id)
            progresos = progresos.filter(curso_id=curso_id)
 
        
        progreso_promedio = progresos.aggregate(promedio=models.Avg('porcentajeCompletado'))['promedio'] or 0
 
        return Response({"progreso_promedio": round(progreso_promedio, 2)}, status=status.HTTP_200_OK)
 
class SimulacionesCompletadasAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
   
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        curso_id = request.query_params.get('curso_id')
 
       
        progresos = Progreso.objects.filter(curso__simulacion=True)
 
       
        if empresa_id:
            
            empresa = get_object_or_404(Empresa, id=empresa_id)
 
            codigos_organizacion = Contrato.objects.filter(
                instructor__empresa_id=empresa_id
            ).values_list('codigoOrganizacion', flat=True).distinct()
 
            progresos = progresos.filter(estudiante__codigoOrganizacion__in=codigos_organizacion)
 
        if curso_id:

            get_object_or_404(Curso, id=curso_id)
 
            progresos = progresos.filter(curso_id=curso_id)
 

        total_simulaciones = progresos.count()
        total_simulaciones_completadas = progresos.filter(simulacionCompletada=True).count()
        porcentaje_completadas = (total_simulaciones_completadas / total_simulaciones * 100) if total_simulaciones > 0 else 0
 

        return Response({
            "total_simulaciones_completadas": total_simulaciones_completadas,
            "total_simulaciones": total_simulaciones,
            "porcentaje_completadas": round(porcentaje_completadas, 2)
        }, status=status.HTTP_200_OK)
 
   
 
class TasaCertificacionAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
   
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        curso_id = request.query_params.get('curso_id')
 
        certificados = Certificado.objects.all()
        if empresa_id:
            empresa = get_object_or_404(Empresa, id=empresa_id)
            instructores = Instructor.objects.filter(empresa_id=empresa_id).values_list('id', flat=True)
            certificados = certificados.filter(curso__instructores_asignados__instructor_id__in=instructores)
        if curso_id:
            curso = get_object_or_404(Curso, id=curso_id)
            certificados = certificados.filter(curso_id=curso_id)
 
       
        estudiantes_certificados = certificados.values_list('estudiante_id', flat=True).distinct()
        total_estudiantes_certificados = estudiantes_certificados.count()
        total_estudiantes = Estudiante.objects.count()
 
        tasa_certificacion = (total_estudiantes_certificados / total_estudiantes * 100) if total_estudiantes > 0 else 0
 
        return Response({"tasa_certificacion": round(tasa_certificacion, 2)}, status=status.HTTP_200_OK)
 
class TasaAprobacionPruebasAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
 
    def get(self, request):
        empresa_id = request.query_params.get('empresa_id')
        curso_id = request.query_params.get('curso_id')
 
 
        pruebas_aprobadas = EstudiantePrueba.objects.filter(estaAprobado=True)
        total_pruebas = EstudiantePrueba.objects.all()
 
        if empresa_id:
         
            empresa = get_object_or_404(Empresa, id=empresa_id)
 
            
            codigos_organizacion = Contrato.objects.filter(
                instructor__empresa_id=empresa_id
            ).values_list('codigoOrganizacion', flat=True).distinct()

            pruebas_aprobadas = pruebas_aprobadas.filter(estudiante__codigoOrganizacion__in=codigos_organizacion)
            total_pruebas = total_pruebas.filter(estudiante__codigoOrganizacion__in=codigos_organizacion)
 

        if curso_id:

            get_object_or_404(Curso, id=curso_id)
 

            pruebas_aprobadas = pruebas_aprobadas.filter(prueba__curso_id=curso_id)
            total_pruebas = total_pruebas.filter(prueba__curso_id=curso_id)
 

        total_aprobados = pruebas_aprobadas.count()
        total_pruebas = total_pruebas.count()
        tasa_aprobacion = (total_aprobados / total_pruebas * 100) if total_pruebas > 0 else 0

        return Response({"tasa_aprobacion": round(tasa_aprobacion, 2)}, status=status.HTTP_200_OK)
 
   
 
class EstudiantesPorEmpresaAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
 
    def get(self, request):
        """
        API para obtener el número total de estudiantes asociados a cada empresa.
        """
        empresas = Empresa.objects.all()
        data = {}
 
        for empresa in empresas:
            
            codigos_organizacion = Contrato.objects.filter(
                instructor__empresa=empresa
            ).values_list('codigoOrganizacion', flat=True).distinct()
 
            
            total_estudiantes = Estudiante.objects.filter(codigoOrganizacion__in=codigos_organizacion).count()
 
          
            data[empresa.nombre] = total_estudiantes
 
        return Response(data, status=status.HTTP_200_OK)
 
   
 
 
class InstructoresPorEmpresaAPIView(APIView):
    authentication_classes = [JWTAuthentication]
   
    permission_classes = [IsAdminUser]
    """
    API para obtener el total de instructores registrados por empresa.
    """
    def get(self, request):
        instructores_por_empresa = Empresa.objects.annotate(total_instructores=models.Count('instructores'))
        data = {empresa.nombre: empresa.total_instructores for empresa in instructores_por_empresa}
 
        return Response(data, status=status.HTTP_200_OK)
   
 
class CursosTasaFinalizacionAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    """
    API para obtener los cursos con mayor y menor tasa de finalización,
    con opción de filtrar por empresa.
    """
    def get(self, request):
        from django.db.models import Avg
 
        
        empresa_id = request.query_params.get('empresa_id', None)
 
       
        cursos_qs = Curso.objects.annotate(
            tasa_finalizacion=Avg('progresos__porcentajeCompletado')
        ).filter(tasa_finalizacion__isnull=False)
 
       
        if empresa_id:
            cursos_qs = cursos_qs.filter(
               
                instructores_asignados__instructor__empresa_id=empresa_id
            )
 
       
        cursos_qs = cursos_qs.order_by('-tasa_finalizacion')
 
       
        mayor_finalizacion = cursos_qs.first() if cursos_qs.exists() else None
        menor_finalizacion = cursos_qs.last() if cursos_qs.exists() else None
 
        data = {
            "curso_mayor_finalizacion": (
                {
                    "titulo": mayor_finalizacion.titulo,
                    "tasa_finalizacion": round(mayor_finalizacion.tasa_finalizacion, 2)
                }
                if mayor_finalizacion
                else None
            ),
            "curso_menor_finalizacion": (
                {
                    "titulo": menor_finalizacion.titulo,
                    "tasa_finalizacion": round(menor_finalizacion.tasa_finalizacion, 2)
                }
                if menor_finalizacion
                else None
            ),
        }
 
        return Response(data, status=status.HTTP_200_OK)
 
 
class EstudianteSubcursoViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = EstudianteSubcurso.objects.all()
    serializer_class = EstudianteSubcursoSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        """
        Filtra la lista de EstudianteSubcurso en base a los parámetros proporcionados.
        """
        queryset = super().get_queryset()
        id_estudiante = self.request.query_params.get('idEstudiante')
        id_subcurso = self.request.query_params.get('idSubcurso')
 
        if id_estudiante:
            queryset = queryset.filter(estudiante_id=id_estudiante)
        if id_subcurso:
            queryset = queryset.filter(subcurso_id=id_subcurso)
 
        return queryset
 
 
class EstudianteModuloViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = EstudianteModulo.objects.all()
    serializer_class = EstudianteModuloSerializer
    permission_classes = [IsAuthenticated]
   
    @action(detail=False, methods=['patch'], url_path='update-completion')
    def update_completion(self, request):
        print("Datos recibidos:", request.data)
        """
        Actualiza el estado de completado para un registro EstudianteModulo.
        Requiere `estudiante_id` y `modulo_id`.
        """
        
        estudiante_id = request.data.get('estudiante_id')
        modulo_id = request.data.get('modulo_id')
        completado = request.data.get('completado', False)
 
        if not estudiante_id or not modulo_id:
            return Response(
                {"error": "Los campos 'estudiante_id' y 'modulo_id' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        try:
           
            estudiante_id = int(estudiante_id)
            modulo_id = int(modulo_id)
 
            
            estudiante_modulo = get_object_or_404(
                EstudianteModulo, estudiante_id=estudiante_id, modulo_id=modulo_id
            )
 
            
            if not isinstance(completado, bool):
                return Response(
                    {"error": "El campo 'completado' debe ser un valor booleano."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
 
           
            estudiante_modulo.completado = completado
            estudiante_modulo.save()
 
            
            serializer = self.get_serializer(estudiante_modulo)
            return Response(serializer.data, status=status.HTTP_200_OK)
 
        except ValueError:
            return Response(
                {"error": "Los campos 'estudiante_id' y 'modulo_id' deben ser enteros."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    @swagger_auto_schema(
        operation_description="Verifica si un módulo está completo para un estudiante dado.",
        manual_parameters=[
            openapi.Parameter(
                'estudiante_id',
                openapi.IN_QUERY,
                description="ID del estudiante",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'modulo_id',
                openapi.IN_QUERY,
                description="ID del módulo",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                "Estado de completado del módulo",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'estudiante_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del estudiante"),
                        'modulo_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID del módulo"),
                        'completado': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Estado de completado"),
                    }
                )
            ),
            400: "Error en los parámetros enviados",
            404: "No se encontró el registro Estudiante-Modulo para los IDs proporcionados",
        }
    )
    @action(detail=False, methods=['get'], url_path='check-completion')
    def check_completion(self, request):
        """
        Verifica si un módulo está completo para un estudiante dado.
        """
        estudiante_id = request.query_params.get('estudiante_id')
        modulo_id = request.query_params.get('modulo_id')

        if not estudiante_id or not modulo_id:
            return Response(
                {"error": "Los parámetros 'estudiante_id' y 'modulo_id' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Convertir a enteros
            estudiante_id = int(estudiante_id)
            modulo_id = int(modulo_id)

            # Obtener el registro EstudianteModulo
            estudiante_modulo = get_object_or_404(
                EstudianteModulo, estudiante_id=estudiante_id, modulo_id=modulo_id
            )

            return Response(
                {
                    "estudiante_id": estudiante_id,
                    "modulo_id": modulo_id,
                    "completado": estudiante_modulo.completado,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError:
            return Response(
                {"error": "Los parámetros 'estudiante_id' y 'modulo_id' deben ser enteros."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Ocurrió un error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
 