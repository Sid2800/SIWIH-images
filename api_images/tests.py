import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from rest_framework.exceptions import ValidationError

from rest_framework import status
from rest_framework.test import APIClient

from api_images.models import (
    FichaBajaDispositivo,
    ImagenDispositivo,
    TipoImagenDispositivo,
    ruta_imagen_dispositivo,
    ruta_miniatura_dispositivo,
)
from api_images.serializers import SubirImagenDispositivoSerializer

from api_images.services.device_image_service import (
    ImagenDispositivoService,
)

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

    def test_rechaza_png_renombrado_como_webp(self):
        contenido = BytesIO()
        Image.new("RGB", (10, 10), "white").save(
            contenido,
            format="PNG",
        )
        archivo = SimpleUploadedFile(
            "imagen_falsa.webp",
            contenido.getvalue(),
            content_type="image/webp",
        )
        datos = self.crear_datos()
        datos["archivo"] = archivo
        serializer = SubirImagenDispositivoSerializer(data=datos)

        self.assertFalse(serializer.is_valid())
        self.assertIn("archivo", serializer.errors)


class ImagenDispositivoServiceTests(TestCase):
    def setUp(self):
        super().setUp()

        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()

        super().tearDown()

    def crear_archivo_webp(self, nombre="equipo.webp"):
        contenido = BytesIO()
        Image.new("RGB", (20, 20), "white").save(
            contenido,
            format="WEBP",
        )
        contenido.seek(0)

        return SimpleUploadedFile(
            nombre,
            contenido.getvalue(),
            content_type="image/webp",
        )

    def crear_datos(
        self,
        dispositivo_id=1,
        tipo_imagen=TipoImagenDispositivo.GENERAL,
        nombre_archivo="equipo.webp",
    ):
        return {
            "dispositivo_id": dispositivo_id,
            "tipo_imagen": tipo_imagen,
            "archivo": self.crear_archivo_webp(nombre_archivo),
            "usuario_snapshot": {
                "id": 1,
                "nombre": "Tecnico de prueba",
            },
        }

    def test_guarda_imagen_miniatura_y_metadatos(self):
        datos = self.crear_datos()
        tamano_original = datos["archivo"].size

        imagen = ImagenDispositivoService(datos).guardar()

        self.assertEqual(ImagenDispositivo.objects.count(), 1)
        self.assertEqual(imagen.tamano, tamano_original)
        self.assertEqual(imagen.formato, "webp")
        self.assertEqual(
            imagen.usuario_creador,
            {"id": 1, "nombre": "Tecnico de prueba"},
        )
        self.assertTrue(imagen.archivo.name.startswith("EQUIPOS/"))
        self.assertTrue(imagen.miniatura.name.startswith("EQUIPOS/"))
        self.assertTrue(
            imagen.archivo.storage.exists(imagen.archivo.name),
        )
        self.assertTrue(
            imagen.miniatura.storage.exists(imagen.miniatura.name),
        )

    def test_rechaza_primera_imagen_distinta_de_general(self):
        datos = self.crear_datos(
            tipo_imagen=TipoImagenDispositivo.INVENTARIO,
        )

        with self.assertRaises(ValidationError):
            ImagenDispositivoService(datos).guardar()

        self.assertEqual(ImagenDispositivo.objects.count(), 0)
        self.assertEqual(
            list(Path(self.media_directory.name).rglob("*.webp")),
            [],
        )

    def test_limpia_archivo_si_falla_la_miniatura(self):
        datos = self.crear_datos()

        with patch(
            "api_images.services.device_image_service.generar_miniatura",
            side_effect=RuntimeError("Fallo de miniatura"),
        ):
            with self.assertRaises(RuntimeError):
                ImagenDispositivoService(datos).guardar()

        self.assertEqual(ImagenDispositivo.objects.count(), 0)
        self.assertEqual(
            list(Path(self.media_directory.name).rglob("*.webp")),
            [],
        )

    def test_rechaza_tipo_repetido_sin_crear_archivos_extra(self):
        ImagenDispositivoService(self.crear_datos()).guardar()

        with self.assertRaises(ValidationError):
            ImagenDispositivoService(self.crear_datos()).guardar()

        self.assertEqual(ImagenDispositivo.objects.count(), 1)
        self.assertEqual(
            len(list(Path(self.media_directory.name).rglob("*.webp"))),
            2,
        )

    def test_rechaza_archivo_sin_extension_webp(self):
        datos = self.crear_datos(nombre_archivo="equipo.png")

        with self.assertRaises(ValidationError):
            ImagenDispositivoService(datos).guardar()

        self.assertEqual(ImagenDispositivo.objects.count(), 0)
        self.assertEqual(
            list(Path(self.media_directory.name).rglob("*.webp")),
            [],
        )

class ImagenDispositivoApiTests(TestCase):
    def setUp(self):
        super().setUp()

        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()

        self.usuario = get_user_model().objects.create_user(
            username="tecnico_api",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.usuario)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()

        super().tearDown()

    def crear_archivo_webp(self):
        contenido = BytesIO()
        Image.new("RGB", (20, 20), "white").save(
            contenido,
            format="WEBP",
        )
        contenido.seek(0)

        return SimpleUploadedFile(
            "equipo.webp",
            contenido.getvalue(),
            content_type="image/webp",
        )

    def crear_datos(
        self,
        dispositivo_id=20,
        tipo_imagen=TipoImagenDispositivo.GENERAL,
    ):
        return {
            "dispositivo_id": dispositivo_id,
            "tipo_imagen": tipo_imagen,
            "archivo": self.crear_archivo_webp(),
            "usuario_snapshot": (
                '{"id": 1, "nombre": "Tecnico API"}'
            ),
        }

    def test_subir_imagen_dispositivo(self):
        response = self.client.post(
            reverse("subir_imagen_dispositivo"),
            data=self.crear_datos(),
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertEqual(ImagenDispositivo.objects.count(), 1)
        self.assertIn(
            "EQUIPOS/",
            response.data["imagen"]["url"],
        )
        self.assertIn(
            "EQUIPOS/",
            response.data["imagen"]["miniatura"],
        )

    def test_consultar_imagenes_dispositivo(self):
        subida = self.client.post(
            reverse("subir_imagen_dispositivo"),
            data=self.crear_datos(dispositivo_id=21),
            format="multipart",
        )
        self.assertEqual(
            subida.status_code,
            status.HTTP_201_CREATED,
            subida.data,
        )

        response = self.client.get(
            reverse(
                "buscar_imagenes_dispositivo",
                kwargs={"dispositivo_id": 21},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cantidad"], 1)
        self.assertEqual(
            response.data["imagenes"][0]["tipo_imagen"],
            TipoImagenDispositivo.GENERAL,
        )

    def test_consulta_sin_imagenes_devuelve_lista_vacia(self):
        response = self.client.get(
            reverse(
                "buscar_imagenes_dispositivo",
                kwargs={"dispositivo_id": 999},
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cantidad"], 0)
        self.assertEqual(response.data["imagenes"], [])

    def test_rechaza_primera_imagen_distinta_de_general(self):
        response = self.client.post(
            reverse("subir_imagen_dispositivo"),
            data=self.crear_datos(
                tipo_imagen=TipoImagenDispositivo.INVENTARIO,
            ),
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(ImagenDispositivo.objects.count(), 0)
        self.assertIn("tipo_imagen", response.data["error"])

    def test_endpoints_requieren_autenticacion(self):
        cliente_sin_autenticacion = APIClient()

        subida = cliente_sin_autenticacion.post(
            reverse("subir_imagen_dispositivo"),
            data=self.crear_datos(),
            format="multipart",
        )
        consulta = cliente_sin_autenticacion.get(
            reverse(
                "buscar_imagenes_dispositivo",
                kwargs={"dispositivo_id": 20},
            )
        )

        self.assertEqual(
            subida.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            consulta.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class EstadoServicioApiTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()
        super().tearDown()

    def test_health_no_requiere_jwt_y_valida_dependencias(self):
        response = APIClient().get(reverse("estado_servicio"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"estado": "ok"})


class FichaBajaDispositivoApiTests(TestCase):
    """Cubre la constancia legal sin afectar las seis fotos del inventario."""

    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()

        self.usuario = get_user_model().objects.create_user(
            username="tecnico_baja_api",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.usuario)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()
        super().tearDown()

    @staticmethod
    def crear_archivo_webp():
        contenido = BytesIO()
        Image.new("RGB", (30, 40), "white").save(
            contenido,
            format="WEBP",
        )
        return SimpleUploadedFile(
            "ficha_baja.webp",
            contenido.getvalue(),
            content_type="image/webp",
        )

    def test_subir_y_consultar_ficha_firmada(self):
        subida = self.client.post(
            reverse("subir_ficha_baja_dispositivo"),
            data={
                "dispositivo_id": 45,
                "archivo": self.crear_archivo_webp(),
                "usuario_snapshot": (
                    '{"id": 1, "nombre": "Tecnico Baja"}'
                ),
            },
            format="multipart",
        )

        self.assertEqual(
            subida.status_code,
            status.HTTP_201_CREATED,
            subida.data,
        )
        self.assertEqual(FichaBajaDispositivo.objects.count(), 1)
        self.assertIn(
            "EQUIPOS/BAJAS/",
            subida.data["ficha"]["url"],
        )

        consulta = self.client.get(
            reverse(
                "buscar_ficha_baja_dispositivo",
                kwargs={"dispositivo_id": 45},
            )
        )
        self.assertEqual(consulta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            consulta.data["ficha"]["uuid"],
            subida.data["ficha"]["uuid"],
        )

    def test_rechaza_segunda_ficha_para_el_mismo_equipo(self):
        datos = {
            "dispositivo_id": 46,
            "archivo": self.crear_archivo_webp(),
        }
        primera = self.client.post(
            reverse("subir_ficha_baja_dispositivo"),
            data=datos,
            format="multipart",
        )
        segunda = self.client.post(
            reverse("subir_ficha_baja_dispositivo"),
            data={
                "dispositivo_id": 46,
                "archivo": self.crear_archivo_webp(),
            },
            format="multipart",
        )

        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FichaBajaDispositivo.objects.count(), 1)

    def test_consulta_sin_ficha_devuelve_null(self):
        respuesta = self.client.get(
            reverse(
                "buscar_ficha_baja_dispositivo",
                kwargs={"dispositivo_id": 999},
            )
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIsNone(respuesta.data["ficha"])

    def test_endpoints_de_ficha_requieren_autenticacion(self):
        cliente = APIClient()

        subida = cliente.post(
            reverse("subir_ficha_baja_dispositivo"),
            data={
                "dispositivo_id": 47,
                "archivo": self.crear_archivo_webp(),
            },
            format="multipart",
        )
        consulta = cliente.get(
            reverse(
                "buscar_ficha_baja_dispositivo",
                kwargs={"dispositivo_id": 47},
            )
        )

        self.assertEqual(subida.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(consulta.status_code, status.HTTP_401_UNAUTHORIZED)
