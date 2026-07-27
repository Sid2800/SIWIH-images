from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from api_images.models import FichaBajaDispositivo
from api_images.utils.main import generar_miniatura


class FichaBajaDispositivoService:
    """Guarda una constancia firmada sin mezclarla con las fotos del equipo."""

    def __init__(self, data):
        self.data = data
        self.ficha = None

    def guardar(self):
        self._validar_webp()

        archivo = self.data["archivo"]
        self.ficha = FichaBajaDispositivo(
            dispositivo_id=self.data["dispositivo_id"],
            archivo=archivo,
            tamano=archivo.size,
            formato="webp",
            usuario_creador=self.data.get("usuario_snapshot"),
        )

        try:
            with transaction.atomic():
                self._validar_unicidad()
                self.ficha.save()
                self._crear_miniatura()
        except IntegrityError as exc:
            self._eliminar_archivos()
            raise ValidationError({
                "dispositivo_id": (
                    "El equipo ya tiene una ficha de baja firmada."
                )
            }) from exc
        except Exception:
            self._eliminar_archivos()
            raise

        return self.ficha

    def _validar_unicidad(self):
        existe = (
            FichaBajaDispositivo.objects
            .select_for_update()
            .filter(dispositivo_id=self.data["dispositivo_id"])
            .exists()
        )
        if existe:
            raise ValidationError({
                "dispositivo_id": (
                    "El equipo ya tiene una ficha de baja firmada."
                )
            })

    def _validar_webp(self):
        archivo = self.data["archivo"]
        if not archivo.name.lower().endswith(".webp"):
            raise ValidationError({
                "archivo": "Se esperaba una imagen WebP."
            })

    def _crear_miniatura(self):
        self.ficha.archivo.open("rb")
        try:
            miniatura = generar_miniatura(self.ficha.archivo)
        finally:
            self.ficha.archivo.close()

        self.ficha.miniatura.save(
            f"thumb_{self.ficha.uuid}.webp",
            miniatura,
            save=False,
        )
        self.ficha.save(update_fields=["miniatura"])

    def _eliminar_archivos(self):
        if self.ficha is None:
            return

        for campo in (self.ficha.miniatura, self.ficha.archivo):
            nombre = getattr(campo, "name", "")
            if not nombre or not nombre.startswith("EQUIPOS/BAJAS/"):
                continue

            almacenamiento = campo.storage
            if almacenamiento.exists(nombre):
                almacenamiento.delete(nombre)
