from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from .views import (
    UsuarioViewSet, AdministradorViewSet, InstructorViewSet, EstudianteViewSet,
    LoginView, RegistroEstudianteAPIView, CursoViewSet,
    SubcursoViewSet, ModuloViewSet, EmpresaViewSet, ModificarInstructorAPIView,
    RegisterInstructorAPIView, CambiarContraseñaAPIView, SubcursosPorCursoAPIView,
    ModulosPorSubcursoAPIView, InstructorCursoAPIView, 
    EstudiantesPorCodigoOrganizacionAPIView, PreguntaViewSet, PruebaViewSet,
    DescargarArchivoModuloAPIView, LoginView,  RegistroEstudianteAPIView
)
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from rest_framework import permissions
from .views import CambiarContraseñaAPIView
from .views import SubcursosPorCursoAPIView
from .views import ModulosPorSubcursoAPIView,InstructorCursoAPIView,EstudiantesPorCodigoOrganizacionAPIView,ProgresoViewSet,EmitirCertificadoAPIView
from .views import EstudianteDashboardAPIView

from .views import DescargarArchivoModuloAPIView

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'administradores', AdministradorViewSet)
router.register(r'instructores', InstructorViewSet)
router.register(r'empresas', EmpresaViewSet)
router.register(r'estudiantes', EstudianteViewSet)
router.register(r'cursos', CursoViewSet)
router.register(r'subcursos', SubcursoViewSet)
router.register(r'modulos', ModuloViewSet)
router.register(r'pruebas', PruebaViewSet, basename='pruebas')  # Solo una vez
router.register(r'preguntas', PreguntaViewSet, basename='preguntas')  # Usar ViewSet para CRUD completo
router.register(r'progreso',ProgresoViewSet)


schema_view = get_schema_view(
   openapi.Info(
      title="API de Capacitaciones Global QHSE",
      default_version='v1',
      description="API para la gestión de usuarios, incluyendo administradores, instructores y clientes.",
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('login/', LoginView.as_view(), name='login'),
    path('cambiarPassword/', CambiarContraseñaAPIView.as_view(), name='cambiar_password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('registroEstudiante/', RegistroEstudianteAPIView.as_view(), name='registro-estudiante'),
    path('modificacionInstructor/', ModificarInstructorAPIView.as_view(), name='modificacion-instructor'),
    path('registrarInstructor/', RegisterInstructorAPIView.as_view(), name='registrar-instructor'),
    path('subcursos/curso/<int:curso_id>/', SubcursosPorCursoAPIView.as_view(), name='subcursos_por_curso'),
    path('modulos/subcurso/<int:subcurso_id>/', ModulosPorSubcursoAPIView.as_view(), name='modulos_por_subcurso'),
    path('modulos/<int:pk>/descargar/', DescargarArchivoModuloAPIView.as_view(), name='descargar_archivo_modulo'),
    path('instructor-curso/', InstructorCursoAPIView.as_view(), name='instructor_curso'),
    path('estudiante-codigoOrganizacion/', EstudiantesPorCodigoOrganizacionAPIView.as_view(), name='estudiante_codigoOrganizacion'),
   path('emitir-certificado/', EmitirCertificadoAPIView.as_view(), name='emitir_certificado'),
   path('estudiante/dashboard/', EstudianteDashboardAPIView.as_view(), name='estudiante_dashboard'),
]
