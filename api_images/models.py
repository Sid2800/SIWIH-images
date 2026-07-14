from django.db import models
from django.db.models import Q
from datetime import datetime
import uuid
from django.utils import timezone



def ruta_imagen(instance, filename):
    fecha = datetime.now().strftime('%Y/%m')
    extension = filename.split('.')[-1]
    return f"{instance.app}/{fecha}/{instance.uuid}.{extension}"


def ruta_miniatura(instance, filename):
    fecha = datetime.now().strftime('%Y/%m')
    return f"{instance.app}/{fecha}/thumb_{instance.uuid}.webp"

def ruta_imagen_usuario(instance, filename):
    return f"USUARIOS/{instance.uuid}.webp"


class TipoPaciente(models.IntegerChoices):
    INTERNO = 1, "INTERNO"
    EXTERNO = 2, "EXTERNO"

# Create your models here.
class ImagenAlmacen(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    app = models.CharField(max_length=20)  # RX, REF, USG, etc
    
    origen_tipo = models.CharField(max_length=50)  # Ej: EvaluacionRxDetalle, Referencia
    origen_id = models.PositiveIntegerField()      # ID real en el HIS
    paciente_id = models.PositiveIntegerField()
    paciente_tipo = models.PositiveSmallIntegerField(
        choices=TipoPaciente.choices,
        default=TipoPaciente.INTERNO,
        db_index=True
    )

    archivo = models.ImageField(upload_to=ruta_imagen)
    miniatura = models.ImageField(upload_to=ruta_miniatura, null=True, blank=True)

    tipo_imagen = models.CharField(max_length=50)  # Torax, Craneo, etc

    tamaño = models.PositiveIntegerField()
    formato = models.CharField(max_length=10)

    fecha_creado = models.DateTimeField(auto_now_add=True)

    activo = models.BooleanField(default=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    fecha_reemplazo = models.DateTimeField(null=True, blank=True)
    usuario_creador = models.JSONField(null=True, blank=True)
    usuario_desactivador = models.JSONField(null=True, blank=True)

    def desactivar(self, usuario_snapshot):
        self.activo = False
        self.fecha_reemplazo = timezone.now()
        self.usuario_desactivador = usuario_snapshot

        self.save(update_fields=[
            "activo",
            "fecha_reemplazo",
            "usuario_desactivador"
        ])

    def siguiente_version(self):
        return self.version + 1

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "app",
                    "origen_tipo",
                    "origen_id",
                    "paciente_tipo",
                    "paciente_id",
                    "activo",
                ]
            ),
        ]


    def __str__(self):
        return str(self.uuid)
    



class ImagenUsuario(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(unique=True, db_index=True)
    imagen = models.ImageField(upload_to=ruta_imagen_usuario)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Imagen usuario {self.user_id}"



class TipoImagenDispositivo(models.TextChoices):
    GENERAL = "GENERAL", "General"
    INVENTARIO = "INVENTARIO", "Inventario"
    PLACA_SERIE = "PLACA_SERIE", "Placa o serie"
    ESTADO_FISICO = "ESTADO_FISICO", "Estado fisico"
    ACCESORIOS = "ACCESORIOS", "Accesorios"
    OTRA = "OTRA", "Otra"


def ruta_imagen_dispositivo(instance, filename):
    fecha = timezone.now().strftime("%Y/%m")
    return f"EQUIPOS/{fecha}/{instance.uuid}.webp"


def ruta_miniatura_dispositivo(instance, filename):
    fecha = timezone.now().strftime("%Y/%m")
    return f"EQUIPOS/{fecha}/thumb_{instance.uuid}.webp"


class ImagenDispositivo(models.Model):
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    dispositivo_id = models.PositiveIntegerField()
    archivo = models.ImageField(upload_to=ruta_imagen_dispositivo)
    miniatura = models.ImageField(
        upload_to=ruta_miniatura_dispositivo,
        null=True,
        blank=True,
    )
    tipo_imagen = models.CharField(
        max_length=50,
        choices=TipoImagenDispositivo.choices,
    )
    tamano = models.PositiveIntegerField()
    formato = models.CharField(max_length=10)
    fecha_creado = models.DateTimeField(auto_now_add=True)
    usuario_creador = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(dispositivo_id__gt=0),
                name="ck_imagen_dispositivo_id_positivo",
            ),
            models.CheckConstraint(
                condition=Q(tipo_imagen__in=TipoImagenDispositivo.values),
                name="ck_imagen_dispositivo_tipo",
            ),
            models.UniqueConstraint(
                fields=["dispositivo_id", "tipo_imagen"],
                name="uq_imagen_dispositivo_tipo",
            ),
        ]

    def __str__(self):
        return f"Equipo {self.dispositivo_id} - {self.tipo_imagen}"
