from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from .views import UsuarioViewSet, AdministradorViewSet, InstructorViewSet, ClienteViewSet, LoginView, Protected, RegistroClienteAPIView
from .views import SimulacionViewSet,CursoViewSet, SubcursoViewSet, ModuloViewSet
from . import views
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework import permissions



router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet)
router.register(r'administradores', AdministradorViewSet)
router.register(r'instructores', InstructorViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'simulaciones',SimulacionViewSet)
router.register(r'cursos',CursoViewSet)
router.register(r'subcursos',SubcursoViewSet)
router.register(r'modulos',ModuloViewSet)

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
    path('completar_modulo/<int:modulo_id>/', views.completar_modulo, name='completar_modulo'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('protected/', Protected.as_view(), name='protected'),
    path('registroCliente/', RegistroClienteAPIView.as_view(), name='registro-cliente'),
   
]
