from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from api_images.models import ImagenDispositivo, TipoImagenDispositivo
from api_images.utils.main import generar_miniatura


class ImagenDispositivoService:
    def __init__(self, data):
        self.data = data
        self.imagen = None

    def guardar(self):
        self._validar_webp()

        archivo = self.data["archivo"]
        self.imagen = ImagenDispositivo(
            dispositivo_id=self.data["dispositivo_id"],
            archivo=archivo,
            tipo_imagen=self.data["tipo_imagen"],
            tamano=archivo.size,
            formato="webp",
            usuario_creador=self.data.get("usuario_snapshot"),
        )

        try:
            with transaction.atomic():
                self._validar_reglas()
                self.imagen.save()
                self._crear_miniatura()
        except IntegrityError as exc:
            self._eliminar_archivos()
            raise ValidationError({
                "tipo_imagen": (
                    "El equipo ya tiene una imagen de este tipo."
                )
            }) from exc
        except Exception:
            self._eliminar_archivos()
            raise

        return self.imagen

    def _validar_reglas(self):
        imagenes = (
            ImagenDispositivo.objects
            .select_for_update()
            .filter(dispositivo_id=self.data["dispositivo_id"])
        )
        cantidad_imagenes = imagenes.count()

        if (
            cantidad_imagenes == 0
            and self.data["tipo_imagen"] != TipoImagenDispositivo.GENERAL
        ):
            raise ValidationError({
                "tipo_imagen": (
                    "La primera imagen del equipo debe ser GENERAL."
                )
            })

        if cantidad_imagenes >= len(TipoImagenDispositivo.values):
            raise ValidationError({
                "dispositivo_id": (
                    "El equipo ya tiene el maximo de seis imagenes."
                )
            })

        if imagenes.filter(
            tipo_imagen=self.data["tipo_imagen"],
        ).exists():
            raise ValidationError({
                "tipo_imagen": (
                    "El equipo ya tiene una imagen de este tipo."
                )
            })

    def _validar_webp(self):
        archivo = self.data["archivo"]

        if not archivo.name.lower().endswith(".webp"):
            raise ValidationError({
                "archivo": "Se esperaba una imagen WebP."
            })

    def _crear_miniatura(self):
        self.imagen.archivo.open("rb")

        try:
            miniatura = generar_miniatura(self.imagen.archivo)
        finally:
            self.imagen.archivo.close()

        self.imagen.miniatura.save(
            f"thumb_{self.imagen.uuid}.webp",
            miniatura,
            save=False,
        )
        self.imagen.save(update_fields=["miniatura"])

    def _eliminar_archivos(self):
        if self.imagen is None:
            return

        for campo in (self.imagen.miniatura, self.imagen.archivo):
            nombre = getattr(campo, "name", "")

            if not nombre or not nombre.startswith("EQUIPOS/"):
                continue

            almacenamiento = campo.storage

            if almacenamiento.exists(nombre):
                almacenamiento.delete(nombre)
