import uuid
from datetime import datetime
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from api_images.models import (
    ImagenDispositivo,
    TipoImagenDispositivo,
    ruta_imagen_dispositivo,
    ruta_miniatura_dispositivo,
)
from api_images.serializers import SubirImagenDispositivoSerializer


class ImagenDispositivoModelTests(TestCase):
    def crear_imagen(
        self,
        dispositivo_id=1,
        tipo_imagen=TipoImagenDispositivo.GENERAL,
    ):
        return ImagenDispositivo.objects.create(
            dispositivo_id=dispositivo_id,
            archivo=f"pruebas/{uuid.uuid4()}.webp",
            tipo_imagen=tipo_imagen,
            tamano=1024,
            formato="webp",
            usuario_creador={"id": 1, "nombre": "Tecnico de prueba"},
        )

    def test_crear_imagen_valida(self):
        imagen = self.crear_imagen()

        self.assertEqual(imagen.dispositivo_id, 1)
        self.assertEqual(imagen.tipo_imagen, TipoImagenDispositivo.GENERAL)
        self.assertEqual(ImagenDispositivo.objects.count(), 1)
        self.assertFalse(imagen.archivo.storage.exists(imagen.archivo.name))

    def test_permite_los_seis_tipos_para_un_dispositivo(self):
        for tipo_imagen in TipoImagenDispositivo.values:
            self.crear_imagen(tipo_imagen=tipo_imagen)

        self.assertEqual(ImagenDispositivo.objects.count(), 6)

    def test_rechaza_tipo_repetido_para_el_mismo_dispositivo(self):
        self.crear_imagen()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_imagen()

    def test_rechaza_dispositivo_id_cero(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_imagen(dispositivo_id=0)

    def test_rechaza_tipo_desconocido(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.crear_imagen(tipo_imagen="DESCONOCIDO")

    def test_genera_rutas_de_equipos_en_webp(self):
        identificador = uuid.UUID("12345678-1234-5678-1234-567812345678")
        imagen = ImagenDispositivo(uuid=identificador)
        instante = timezone.make_aware(datetime(2026, 7, 14, 12, 0))

        with patch("api_images.models.timezone.now", return_value=instante):
            ruta_archivo = ruta_imagen_dispositivo(imagen, "original.png")
            ruta_miniatura = ruta_miniatura_dispositivo(
                imagen,
                "miniatura.png",
            )

        self.assertEqual(
            ruta_archivo,
            f"EQUIPOS/2026/07/{identificador}.webp",
        )
        self.assertEqual(
            ruta_miniatura,
            f"EQUIPOS/2026/07/thumb_{identificador}.webp",
        )
class SubirImagenDispositivoSerializerTests(TestCase):
    def crear_archivo_webp(self, nombre="equipo.webp"):
        contenido = BytesIO()
        Image.new("RGB", (10, 10), "white").save(
            contenido,
            format="WEBP",
        )
        contenido.seek(0)

        return SimpleUploadedFile(
            nombre,
            contenido.getvalue(),
            content_type="image/webp",
        )

    def crear_registro(
        self,
        dispositivo_id=1,
        tipo_imagen=TipoImagenDispositivo.GENERAL,
    ):
        return ImagenDispositivo.objects.create(
            dispositivo_id=dispositivo_id,
            archivo=f"pruebas/{uuid.uuid4()}.webp",
            tipo_imagen=tipo_imagen,
            tamano=1024,
            formato="webp",
        )

    def crear_datos(
        self,
        dispositivo_id=1,
        tipo_imagen=TipoImagenDispositivo.GENERAL,
        usuario_snapshot='{"id": 1, "nombre": "Tecnico"}',
    ):
        return {
            "dispositivo_id": dispositivo_id,
            "tipo_imagen": tipo_imagen,
            "archivo": self.crear_archivo_webp(),
            "usuario_snapshot": usuario_snapshot,
        }

    def test_acepta_general_como_primera_imagen(self):
        serializer = SubirImagenDispositivoSerializer(
            data=self.crear_datos(),
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["usuario_snapshot"],
            {"id": 1, "nombre": "Tecnico"},
        )

    def test_rechaza_primera_imagen_que_no_sea_general(self):
        serializer = SubirImagenDispositivoSerializer(
            data=self.crear_datos(
                tipo_imagen=TipoImagenDispositivo.INVENTARIO,
            ),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("tipo_imagen", serializer.errors)

    def test_acepta_segundo_tipo_diferente(self):
        self.crear_registro()

        serializer = SubirImagenDispositivoSerializer(
            data=self.crear_datos(
                tipo_imagen=TipoImagenDispositivo.INVENTARIO,
            ),
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rechaza_tipo_repetido(self):
        self.crear_registro()

        serializer = SubirImagenDispositivoSerializer(
            data=self.crear_datos(),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("tipo_imagen", serializer.errors)

    def test_rechaza_mas_de_seis_imagenes(self):
        for tipo_imagen in TipoImagenDispositivo.values:
            self.crear_registro(
                dispositivo_id=2,
                tipo_imagen=tipo_imagen,
            )

        serializer = SubirImagenDispositivoSerializer(
            data=self.crear_datos(
                dispositivo_id=2,
                tipo_imagen=TipoImagenDispositivo.GENERAL,
            ),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("dispositivo_id", serializer.errors)

    def test_rechaza_usuario_snapshot_que_no_sea_objeto(self):
        serializer = SubirImagenDispositivoSerializer(
            data=self.crear_datos(
                usuario_snapshot='["usuario", "incorrecto"]',
            ),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("usuario_snapshot", serializer.errors)
