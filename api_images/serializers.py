from rest_framework import serializers
from .models import ImagenAlmacen
from .models import TipoPaciente
from api_images.validators.validators import validar_app, validar_origen_tipo, validar_imagen
from rest_framework.exceptions import ValidationError
import json

class ImagenAlmacenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenAlmacen
        fields = "__all__"


class SubirImagenUsuarioSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField(min_value=1)
    archivo = serializers.ImageField(validators=[validar_imagen])


class BuscarImagenesUsuarioSerializer(serializers.Serializer):
    usuarios_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False
    )


class SubirImagenSerializer(serializers.Serializer):
    app = serializers.CharField(validators=[validar_app])
    origen_tipo = serializers.CharField(validators=[validar_origen_tipo])
    origen_id = serializers.IntegerField(min_value=1)
    paciente_id = serializers.IntegerField(min_value=1)
    paciente_tipo = serializers.ChoiceField(
        choices=TipoPaciente.choices
    )
    tipo_imagen = serializers.CharField()
    archivo = serializers.ImageField(validators=[validar_imagen])

    usuario_snapshot = serializers.CharField(required=False)

    def validate(self, data):
        usuario_snapshot = data.get("usuario_snapshot")

        if usuario_snapshot:
            try:
                data["usuario_snapshot"] = json.loads(usuario_snapshot)
            except json.JSONDecodeError:
                raise ValidationError({
                    "usuario_snapshot": "Debe ser JSON válido"
                })

        return data





class DesactivarImagenSerializer(serializers.Serializer):
    app = serializers.CharField(validators=[validar_app])
    origen_tipo = serializers.CharField(validators=[validar_origen_tipo])
    paciente_id = serializers.IntegerField(min_value=1)
    paciente_tipo = serializers.ChoiceField(
        choices=TipoPaciente.choices
    )
    origen_id = serializers.IntegerField(min_value=1)
    usuario_snapshot = serializers.CharField(required=False)

    def validate(self, data):
        usuario_snapshot = data.get("usuario_snapshot")

        if usuario_snapshot:
            try:
                data["usuario_snapshot"] = json.loads(usuario_snapshot)
            except json.JSONDecodeError:
                raise ValidationError({
                    "usuario_snapshot": "Debe ser JSON válido"
                })
        return data
    

class DesactivarImagenesBatchSerializer(serializers.Serializer):
    app = serializers.CharField(validators=[validar_app])
    origen_tipo = serializers.CharField(validators=[validar_origen_tipo])
    paciente_id = serializers.IntegerField(min_value=1)
    paciente_tipo = serializers.ChoiceField(
        choices=TipoPaciente.choices
    )
    origen_ids = serializers.ListField(
            child=serializers.IntegerField(min_value=1),
            allow_empty=False,
        )
    usuario_snapshot = serializers.CharField(required=False)

    def validate(self, data):
        usuario_snapshot = data.get("usuario_snapshot")

        if usuario_snapshot:
            try:
                data["usuario_snapshot"] = json.loads(usuario_snapshot)
            except json.JSONDecodeError:
                raise ValidationError({
                    "usuario_snapshot": "Debe ser JSON válido"
                })
        return data
    

class CambiarReferenciaImagenesSerializer(serializers.Serializer):
    paciente_interno_id = serializers.IntegerField(min_value=1)
    paciente_externo_id = serializers.IntegerField(min_value=1)

    def validate(self, data):
        if data["paciente_externo_id"] == data["paciente_interno_id"]:
            raise serializers.ValidationError(
                "El paciente externo y el interno no pueden ser iguales."
            )
        return data





class BuscarImagenesSerializer(serializers.Serializer):
    app = serializers.CharField(validators=[validar_app])
    origen_tipo = serializers.CharField(validators=[validar_origen_tipo])
    paciente_id = serializers.IntegerField(min_value=1)
    paciente_tipo = serializers.ChoiceField(
        choices=TipoPaciente.choices
    )
    origen_ids = serializers.ListField(
            child=serializers.IntegerField(min_value=1),
            allow_empty=False,
        )

    def validate(self, data):
        return data


class IdentificarImagenSerializer(serializers.Serializer):
    app = serializers.CharField(validators=[validar_app])
    origen_tipo = serializers.CharField(validators=[validar_origen_tipo])
    origen_id = serializers.IntegerField(min_value=1)
    paciente_id = serializers.IntegerField(min_value=1)
    tipo_imagen = serializers.CharField()