from rest_framework import serializers
from .models import Usuario, Administrador, Instructor, Cliente, Simulacion, Curso, Subcurso, Modulo
from django.contrib.auth import authenticate



class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'


class AdministradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrador
        fields = ['first_name','last_name', 'email', 'password', 'empresa', 'codigoOrganizacion']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Administrador(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
    
class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ['first_name','last_name', 'email', 'password','area', 'fechaInicioContrato', 'fechaFinContrato', 'empresa']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Instructor(**validated_data)
        temp_password = user.generar_contraseña_temporal()  
        user.set_password(temp_password) 
        user.save()
        return user

"""""
class InstructorReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ['username', 'email', 'password', 'area', 'fechaInicioContrato', 'fechaFinContrato', 'empresa','codigoOrganizacion']
        extra_kwargs = {'password': {'write_only': True}}   #ESTO DEFINE SI TRAE LA INFO O NO LA API O SEA LA CONTRASEÑA
"""
class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['first_name','last_name', 'email', 'password', 'empresa', 'codigoOrganizacion', 'asignadoSimulacion']
        extra_kwargs = {'password': {'write_only': True}}
    def validate_email(self, value):
        
        if Cliente.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value
    def create(self, validated_data):
        user = Cliente(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginResponseSerializer(serializers.ModelSerializer):
    tipo_usuario = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['first_name','last_name', 'email', 'empresa', 'tipo_usuario']  

    def get_tipo_usuario(self, obj):

        if isinstance(obj, Administrador):
            return "Administrador"
        elif isinstance(obj, Instructor):
            return "Instructor"
        elif isinstance(obj, Cliente):
            return "Cliente"
        return "Usuario"

class AdministradorDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Administrador
        fields = LoginResponseSerializer.Meta.fields + ['codigoOrganizacion', 'is_staff', 'is_superuser','empresa']  

class InstructorDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Instructor
        fields = LoginResponseSerializer.Meta.fields + ['area', 'fechaInicioContrato', 'fechaFinContrato', 'codigoOrganizacion','empresa']  

class ClienteDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Cliente
        fields = LoginResponseSerializer.Meta.fields + ['asignadoSimulacion', 'codigoOrganizacion','empresa']  


class SimulacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Simulacion
        fields = '__all__'


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = '__all__'

class SubcursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcurso
        fields = '__all__'

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = '__all__'