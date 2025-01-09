from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from .views import UsuarioViewSet, AdministradorViewSet, InstructorViewSet, EstudianteViewSet, LoginView,  RegistroEstudianteAPIView
from .views import CursoViewSet, SubcursoViewSet, ModuloViewSet,EmpresaViewSet,ModificarInstructorAPIView,RegisterInstructorAPIView
from . import views
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework import permissions
from .views import CambiarContraseñaAPIView,CrearContratosAPIView,ObtenerContratosAPIView,EliminarContratosAPIView,ActualizarContratosAPIView
from .views import SubcursosPorCursoAPIView,EstudiantePruebaViewSet,CertificadoAPIView,ContratosPorInstructorAPIView
from .views import ModulosPorSubcursoAPIView,ContratoAPIView,EstudiantesPorCodigoOrganizacionAPIView,ProgresoViewSet,EmitirCertificadoAPIView
from .views import DescargarArchivoModuloAPIView,ActualizarEstudiantePruebaAPIView,EstudianteModuloViewSet,EstudianteSubcursoViewSet
from .views import EmpresasTotalesAPIView,UsuariosTotalesAPIView,CursosTotalesAPIView,ProgresoPromedioAPIView,SimulacionesCompletadasAPIView
from .views import FilteredMetricsAPIView,GeneralMetricsAPIView,VRLoginView,InstructorGeneralMetricsAPIView,InstructorCursosTasaFinalizacionAPIView
from .views import TasaCertificacionAPIView,TasaAprobacionPruebasAPIView,EstudiantesPorEmpresaAPIView,InstructoresPorEmpresaAPIView,CursosTasaFinalizacionAPIView
router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'administradores', AdministradorViewSet)
router.register(r'instructores', InstructorViewSet)
router.register(r'empresas', EmpresaViewSet)
router.register(r'estudiantes', EstudianteViewSet)

router.register(r'cursos',CursoViewSet)
router.register(r'subcursos',SubcursoViewSet)
router.register(r'modulos',ModuloViewSet)
router.register(r'progreso',ProgresoViewSet)
router.register(r'estudiantePrueba',EstudiantePruebaViewSet)
router.register(r'estudianteSubcurso',EstudianteSubcursoViewSet)
router.register(r'estudianteModulo',EstudianteModuloViewSet)


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
    path('login-vr/', VRLoginView.as_view(), name='login_vr'),
    path('cambiarPassword/', CambiarContraseñaAPIView.as_view(), name='cambiar_password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('registroEstudiante/', RegistroEstudianteAPIView.as_view(), name='registro-estudiante'),
    path('modificacionInstructor/', ModificarInstructorAPIView.as_view(), name='modificacion-instructor'),
    path('registrarInstructor/', RegisterInstructorAPIView.as_view(), name='registrar-instructor'),
    path('subcursos/curso/<int:curso_id>/', SubcursosPorCursoAPIView.as_view(), name='subcursos_por_curso'),
    path('modulos/subcurso/<int:subcurso_id>/', ModulosPorSubcursoAPIView.as_view(), name='modulos_por_subcurso'),
    path('modulos/<int:pk>/descargar/', DescargarArchivoModuloAPIView.as_view(), name='descargar_archivo_modulo'),
    path('contrato/', ContratoAPIView.as_view(), name='contrato'),
    path('estudiante-codigoOrganizacion/', EstudiantesPorCodigoOrganizacionAPIView.as_view(), name='estudiante_codigoOrganizacion'),
    path('emitir-certificado/', EmitirCertificadoAPIView.as_view(), name='emitir_certificado'),
    path('certificado/', CertificadoAPIView.as_view(), name='certificado'),
    path('actualizar-prueba/', ActualizarEstudiantePruebaAPIView.as_view(), name='actualizar_prueba'),
    path('empresas-total/', EmpresasTotalesAPIView.as_view(), name='empresas_total'),
    path('usuarios-total/', UsuariosTotalesAPIView.as_view(), name='usuarios_total'),
    path('cursos-total/', CursosTotalesAPIView.as_view(), name='cursos_total'),
    path('progreso-promedio/', ProgresoPromedioAPIView.as_view(), name='progreso_promedio'),
    path('simulaciones-completadas/', SimulacionesCompletadasAPIView.as_view(), name='simulaciones_completadas'),
    path('tasa-certificacion/', TasaCertificacionAPIView.as_view(), name='tasa_certificacion'),
    path('tasa-aprobacion/', TasaAprobacionPruebasAPIView.as_view(), name='tasa_aprobacion'),
    path('estudiante-empresa/', EstudiantesPorEmpresaAPIView.as_view(), name='estudiante_empresa'),
    path('instructor-empresa/', InstructoresPorEmpresaAPIView.as_view(), name='instructor_empresa'),
    path('cursos-finalizacion/', CursosTasaFinalizacionAPIView.as_view(), name='cursos_finalizacion'),
    path('crear-contrato/', CrearContratosAPIView.as_view(), name='crear_contrato'),
    path('actualizar-contrato/', ActualizarContratosAPIView.as_view(), name='actualizar_contrato'),
    path('obtener-contrato/', ObtenerContratosAPIView.as_view(), name='obtener_contrato'),
    path('eliminar-contrato/', EliminarContratosAPIView.as_view(), name='eliminar_contrato'),
    path('obtener-contrato-por-instructor/', ContratosPorInstructorAPIView.as_view(), name='obtener_contrato_por_instructor'),
    path('metricas-general/', GeneralMetricsAPIView.as_view(), name='metricas_general'),
    path('metricas-filtro/', FilteredMetricsAPIView.as_view(), name='metricas_filtro'),
    path('metricas-instructor/', InstructorGeneralMetricsAPIView.as_view(), name='metricas_instructor'),
    path('metricas-instructor-finalizacion/', InstructorCursosTasaFinalizacionAPIView.as_view(), name='metricas_instructor_finalizacion'),

   
   
]
