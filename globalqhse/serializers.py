from rest_framework import serializers
from .models import Usuario, Administrador, Instructor, Estudiante, Curso, Subcurso, Modulo, Empresa,InstructorCurso,Progreso,EstudiantePrueba, Pregunta, Prueba
from .utils.email import EmailService
import random
import string
import json

from rest_framework.response import Response

import secrets
from rest_framework.exceptions import ValidationError


class PasswordValidationMixin:
    def validate_password(self, value):
        """
        Validar que la contraseña cumpla con los requisitos mínimos de seguridad.
        """
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("La contraseña debe contener al menos un número.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("La contraseña debe contener al menos una letra.")
        return value


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'


class AdministradorSerializer(PasswordValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Administrador
        fields = ['first_name', 'last_name', 'email', 'password', 'cargo']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        """
        Crear un nuevo administrador con contraseña hasheada.
        """
        try:
            user = Administrador(**validated_data)
            user.set_password(validated_data['password'])  # Hash de la contraseña
            user.save()
            return user
        except Exception as e:
            raise serializers.ValidationError(f"Ocurrió un error al crear el administrador: {str(e)}")

    
class InstructorSerializer(PasswordValidationMixin, serializers.ModelSerializer):

    empresa_nombre = serializers.SerializerMethodField()
    class Meta:
        model = Instructor
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'area', 
                  'fechaInicioCapacitacion', 'fechaFinCapacitacion', 
                  'codigoOrganizacion', 'is_active','empresa','empresa_nombre']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def get_empresa_nombre(self, obj):
        """
        Retorna el nombre de la empresa asociada al instructor.
        """
        return obj.empresa.nombre if obj.empresa else None 

    def create(self, validated_data):
        """
        Crear un nuevo instructor con una contraseña temporal.
        """
        try:
            user = Instructor(**validated_data)
            temp_password = user.generar_contraseña_temporal()  # Generar contraseña temporal
            user.set_password(temp_password)  # Hash de la contraseña temporal
            user.save()
            return user
        except Exception as e:
            raise serializers.ValidationError(f"Ocurrió un error al crear el instructor: {str(e)}")

class RegisterInstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = [
            'first_name', 'last_name', 'email', 'area',
            'fechaInicioCapacitacion', 'fechaFinCapacitacion', 'empresa'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        self.rol = 'instructor'
        try:
            # Crear el instructor sin contraseña ni codigoOrganizacion
            instructor = Instructor(**validated_data)

            # Generar codigoOrganizacion automáticamente
            prefix = instructor.empresa.nombre[:3].upper()
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            instructor.codigoOrganizacion = f"{prefix}-{suffix}"

            # Generar contraseña temporal
            temp_password = secrets.token_urlsafe(10)
            instructor.set_password(temp_password)  # Hashearla
            instructor.save()

            # Enviar la contraseña temporal por correo
            email_service = EmailService(
                to_email=instructor.email,
                subject='Bienvenido a la organización',
                body=f"""
                Hola {instructor.first_name},

                Su cuenta ha sido creada exitosamente. Aquí están sus credenciales de acceso:

                - Código de organización: {instructor.codigoOrganizacion}
                - Contraseña temporal: {temp_password}

                Por favor, cambie su contraseña después de iniciar sesión.

                Saludos,
                Equipo de Global QHSE
                """
            )
            email_service.send_email()

            return instructor
        except Exception as e:
            raise serializers.ValidationError(f"Ocurrió un error al crear el instructor: {str(e)}")


class EstudianteSerializer(PasswordValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Estudiante
        fields = ['id','first_name', 'last_name', 'email', 'password', 
                   'codigoOrganizacion']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        """
        Validar que el email no esté registrado.
        """
        if Estudiante.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value

    def create(self, validated_data):
        """
        Crear un nuevo estudiante con contraseña hasheada.
        """
        try:
            user = Estudiante(**validated_data)
            user.set_password(validated_data['password'])  # Hash de la contraseña
            user.save()
            return user
        except Exception as e:
            raise serializers.ValidationError(f"Ocurrió un error al crear el estudiante: {str(e)}")


class LoginResponseSerializer(serializers.ModelSerializer):
    #tipo_usuario = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id','first_name','last_name', 'email','rol']  



class AdministradorDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Administrador
        fields = LoginResponseSerializer.Meta.fields + ['cargo', 'is_staff', 'is_superuser']  

class InstructorDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Instructor
        fields = LoginResponseSerializer.Meta.fields + ['area', 'fechaInicioCapacitacion', 'fechaFinCapacitacion', 'codigoOrganizacion','is_active','debeCambiarContraseña']  

class EstudianteDetailSerializer(LoginResponseSerializer):
    class Meta(LoginResponseSerializer.Meta):
        model = Estudiante
        fields = LoginResponseSerializer.Meta.fields + ['codigoOrganizacion','is_active']  





class CursoSerializer(serializers.ModelSerializer):
    has_prueba = serializers.SerializerMethodField()
    prueba_id = serializers.SerializerMethodField()

    class Meta:
        model = Curso
        fields = '__all__'  # Incluye todos los campos del modelo más los campos adicionales

    def get_has_prueba(self, obj):
        return hasattr(obj, 'prueba')

    def get_prueba_id(self, obj):
        return obj.prueba.id if hasattr(obj, 'prueba') else None

class SubcursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcurso
        fields = '__all__'

class ModuloSerializer(serializers.ModelSerializer):
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = Modulo
        fields = ['id', 'nombre', 'enlace', 'archivo_url','subcurso','archivo']  # Incluye otros campos relevantes

    def get_archivo_url(self, obj):
        request = self.context.get('request')  # Asegúrate de pasar el `request` al serializer en la vista
        if obj.archivo and hasattr(obj.archivo, 'url'):
            return request.build_absolute_uri(obj.archivo.url)
        return None
    def update(self, instance, validated_data):
        archivo = validated_data.get('archivo', None)
        if archivo is not None:
            instance.archivo = archivo  # Actualizar si se envía
        instance.nombre = validated_data.get('nombre', instance.nombre)
        instance.enlace = validated_data.get('enlace', instance.enlace)
        instance.save()
        return instance

class InstructorCursoSerializer(serializers.ModelSerializer):
    instructor_email = serializers.EmailField(source='instructor.email', read_only=True)
    curso_titulo = serializers.CharField(source='curso.titulo', read_only=True)
    curso_id=serializers.IntegerField(source='curso.id', read_only=True)

    class Meta:
        model = InstructorCurso
        fields = ['id', 'instructor', 'instructor_email','curso_id', 'curso', 'curso_titulo', 'fecha_asignacion']
        extra_kwargs = {
            'instructor': {'write_only': True},
            'curso': {'write_only': True},
        }

class ProgresoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Progreso
        fields = '__all__'


class EstudiantePruebaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstudiantePrueba
        fields = ['estaAprobado', 'calificacion']


class PreguntaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pregunta
        fields = ['id', 'prueba', 'pregunta', 'opcionesRespuestas', 'respuestaCorrecta', 'puntajePregunta']
        read_only_fields = ['id']  # Removed 'prueba'

    def validate(self, attrs):
        opciones = attrs.get('opcionesRespuestas')
        respuesta_correcta = attrs.get('respuestaCorrecta')

        if not isinstance(opciones, dict):
            raise serializers.ValidationError({"opcionesRespuestas": "Debe ser un objeto JSON válido."})

        if respuesta_correcta not in opciones.values():
            raise serializers.ValidationError({"respuestaCorrecta": "La respuesta correcta debe estar entre las opciones de respuesta."})

        return attrs


class PruebaSerializer(serializers.ModelSerializer):
    preguntas = PreguntaSerializer(many=True, required=False)

    class Meta:
        model = Prueba
        fields = ['id', 'curso', 'duracion', 'fechaCreacion', 'preguntas']
        read_only_fields = ['id', 'fechaCreacion']

    def validate_curso(self, value):
        if Prueba.objects.filter(curso=value).exists():
            raise serializers.ValidationError("Este curso ya tiene una prueba asociada.")
        return value

    def create(self, validated_data):
        preguntas_data = validated_data.pop('preguntas', [])
        prueba = Prueba.objects.create(**validated_data)
        for pregunta_data in preguntas_data:
            Pregunta.objects.create(prueba=prueba, **pregunta_data)
        return prueba

    def update(self, instance, validated_data):
        preguntas_data = validated_data.pop('preguntas', [])
        instance.duracion = validated_data.get('duracion', instance.duracion)
        instance.save()
        # La gestión de Preguntas se maneja por separado
        return instance
 
class PreguntaParaPruebaExistenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pregunta
        fields = ['pregunta', 'opcionesRespuestas', 'respuestaCorrecta', 'puntajePregunta']

    def validate(self, data):
        if ";" not in data.get('opcionesRespuestas', ''):
            raise serializers.ValidationError(
                {"opcionesRespuestas": "Debe incluir al menos dos opciones separadas por ';'."}
            )
        return data

class PruebaConPreguntasSerializer(serializers.ModelSerializer):
    preguntas = PreguntaSerializer(many=True, write_only=True)

    class Meta:
        model = Prueba
        fields = ['curso', 'duracion', 'fechaCreacion', 'preguntas']

    def validate_curso(self, value):
        # Verifica si ya existe una prueba para este curso
        if Prueba.objects.filter(curso=value).exists():
            raise ValidationError("Ya existe una prueba asociada a este curso.")
        return value

    def create(self, validated_data):
        preguntas_data = validated_data.pop('preguntas', [])
        prueba = Prueba.objects.create(**validated_data)
        for p_data in preguntas_data:
            Pregunta.objects.create(prueba=prueba, **p_data)
        return prueba



   