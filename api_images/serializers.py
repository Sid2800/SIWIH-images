from rest_framework import serializers
from .models import (
    ImagenAlmacen,
    ImagenDispositivo,
    TipoImagenDispositivo,
    TipoPaciente,
)
from api_images.validators.validators import (
    validar_app,
    validar_origen_tipo,
    validar_imagen,
)
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

    def validate(self, data): return data


class IdentificarImagenSerializer(serializers.Serializer):
    app = serializers.CharField(validators=[validar_app])
    origen_tipo = serializers.CharField(validators=[validar_origen_tipo])
    origen_id = serializers.IntegerField(min_value=1)
    paciente_id = serializers.IntegerField(min_value=1)
    tipo_imagen = serializers.CharField()

class SubirImagenDispositivoSerializer(serializers.Serializer):
    dispositivo_id = serializers.IntegerField(min_value=1)
    tipo_imagen = serializers.ChoiceField(
        choices=TipoImagenDispositivo.choices,
    )
    archivo = serializers.ImageField(validators=[validar_imagen])
    usuario_snapshot = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, data):
        dispositivo_id = data["dispositivo_id"]
        tipo_imagen = data["tipo_imagen"]

        imagenes = ImagenDispositivo.objects.filter(
            dispositivo_id=dispositivo_id,
        )
        cantidad_imagenes = imagenes.count()

        if (
            cantidad_imagenes == 0
            and tipo_imagen != TipoImagenDispositivo.GENERAL
        ):
            raise ValidationError({
                "tipo_imagen": (
                    "La primera imagen del equipo debe ser GENERAL."
                )
            })

        if cantidad_imagenes >= len(TipoImagenDispositivo.values):
            raise ValidationError({
                "dispositivo_id": (
                    "El equipo ya tiene el máximo de seis imágenes."
                )
            })

        if imagenes.filter(tipo_imagen=tipo_imagen).exists():
            raise ValidationError({
                "tipo_imagen": (
                    "El equipo ya tiene una imagen de este tipo."
                )
            })

        usuario_snapshot = data.get("usuario_snapshot")

        if not usuario_snapshot:
            data["usuario_snapshot"] = None
            return data

        try:
            usuario_snapshot = json.loads(usuario_snapshot)
        except json.JSONDecodeError:
            raise ValidationError({
                "usuario_snapshot": "Debe ser JSON válido."
            })

        if not isinstance(usuario_snapshot, dict):
            raise ValidationError({
                "usuario_snapshot": "Debe ser un objeto JSON."
            })

        data["usuario_snapshot"] = usuario_snapshot
        return data
