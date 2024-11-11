from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .models import Usuario, Administrador, Instructor, Cliente, Simulacion, Curso, Subcurso, Modulo
from rest_framework.views import APIView
from .serializers import UsuarioSerializer, AdministradorSerializer, InstructorSerializer,ClienteSerializer, CursoSerializer
from .serializers import AdministradorDetailSerializer,InstructorDetailSerializer,ClienteDetailSerializer,LoginResponseSerializer
from .serializers import SimulacionSerializer, SubcursoSerializer, ModuloSerializer
from django.contrib.auth import authenticate
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .utils.email import EmailService
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser, FormParser




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
    #permission_classes = [IsAuthenticated] 

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)  
        if serializer.is_valid():
            instructor = serializer.save()  
            temp_password = instructor.generar_contraseña_temporal()  # Generar contraseña temporal y guardarla
            
            email_service = EmailService(
                to_email=instructor.email,
                subject='Cuenta creada correctamente. Bienvenido a Nuestra Organización',
                body=f'Su cuenta de instructor ha sido creada. Su código de organización es {instructor.codigoOrganizacion}. Su contraseña temporal es: {temp_password}'
            )
            email_service.send_email()

            response_data = serializer.data  
            response_data['temp_password'] = temp_password  
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ClienteViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated] 

    @action(detail=False, methods=['post'])
    def crear(self, request):
        serializer = ClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class RegistroClienteAPIView(APIView):
    
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=ClienteSerializer,
        responses={201: ClienteSerializer, 400: 'Bad Request'}
    )

    def post(self, request):
        
        codigo_organizacion = request.data.get('codigoOrganizacion')

        
        instructor = Instructor.objects.filter(codigoOrganizacion=codigo_organizacion).first()
        if not instructor:
            return Response(
                {"error": "El código de organización no es válido o no está asociado a un instructor."},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        request.data['empresa'] = instructor.empresa

        
        serializer = ClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    @swagger_auto_schema(
        operation_description="Inicia sesión y autentica a un usuario, devolviendo el tipo de usuario, sus detalles y un token JWT.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Contraseña'),
            }
        ),
        responses={
            200: 'Detalle del usuario autenticado con token',
            401: 'Credenciales inválidas',
            403: 'Cuenta desactivada'
        }
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

       
        
        user = authenticate(request, email=email, password=password)

        
        if user is not None:
            if user.is_active:
                
                try:
                    user = Administrador.objects.get(pk=user.pk)
                except Administrador.DoesNotExist:
                    try:
                        user = Instructor.objects.get(pk=user.pk)
                    except Instructor.DoesNotExist:
                        try:
                            user = Cliente.objects.get(pk=user.pk)
                        except Cliente.DoesNotExist:
                            user = Usuario.objects.get(pk=user.pk)
                
                
                if isinstance(user, Administrador):
                    serializer = AdministradorDetailSerializer(user)
                elif isinstance(user, Instructor):
                    serializer = InstructorDetailSerializer(user)
                elif isinstance(user, Cliente):
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
        

class Protected(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]  # Solo usuarios autenticados pueden acceder

    def get(self, request):
        return Response({"mensaje": "Acceso permitido solo para usuarios autenticados."})
    
class SimulacionViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    queryset = Simulacion.objects.all()
    serializer_class = SimulacionSerializer
    permission_classes = [IsAuthenticated] 

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

@api_view(['POST'])
def completar_modulo(request, modulo_id):
    """Vista para marcar un módulo como completado y actualizar el progreso del subcurso."""
    modulo = get_object_or_404(Modulo, id=modulo_id)
    modulo.completado = True
    modulo.save()  # Guarda el estado de completado en el módulo

    # Llama al método actualizar_progreso en el subcurso asociado
    modulo.subcurso.actualizar_progreso()

    return Response({'message': 'Módulo completado y progreso actualizado'}, status=status.HTTP_200_OK)