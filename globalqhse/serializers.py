from rest_framework import serializers
from .models import Usuario, Administrador, Instructor, Estudiante, Simulacion, Curso, Subcurso, Modulo, Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'


class AdministradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrador
        fields = ['first_name','last_name', 'email', 'password', 'cargo']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Administrador(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user
    
class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ['id','first_name','last_name', 'email', 'password','area', 'fechaInicioCapacitacion', 'fechaFinCapacitacion', 'codigoOrganizacion','is_active']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = Instructor(**validated_data)
        temp_password = user.generar_contraseña_temporal()  
        user.set_password(temp_password) 
        user.save()
        return user


class EstudaianteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estudiante
        fields = ['first_name','last_name', 'email', 'password', 'asignadoSimulacion']
        extra_kwargs = {'password': {'write_only': True}}
    def validate_email(self, value):
        
        if Estudiante.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value
    def create(self, validated_data):
        user = Estudiante(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginResponseSerializer(serializers.ModelSerializer):
    tipo_usuario = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['first_name','last_name', 'email', 'tipo_usuario']  

    def get_tipo_usuario(self, obj):

        if isinstance(obj, Administrador):
            return "Administrador"
        elif isinstance(obj, Instructor):
            return "Instructor"
        elif isinstance(obj, Estudiante):
            return "Estudiante"
        return "Usuario"

class AdministradorDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Administrador
        fields = LoginResponseSerializer.Meta.fields + ['cargo', 'is_staff', 'is_superuser']  

class InstructorDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Instructor
        fields = LoginResponseSerializer.Meta.fields + ['area', 'fechaInicioCapacitacion', 'fechaFinCapacitacion', 'codigoOrganizacion','is_active']  

class ClienteDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Estudiante
        fields = LoginResponseSerializer.Meta.fields + ['asignadoSimulacion']  


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