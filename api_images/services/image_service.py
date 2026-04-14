from django.db import transaction
from django.utils import timezone
from api_images.models import ImagenAlmacen
from api_images.utils.main import convertir_a_webp,generar_miniatura
from rest_framework.exceptions import ValidationError

class ImagenService:

    def __init__(self, data):
        self.data = data
        self.archivo_webp = None

    def sincronizar(self):
        with transaction.atomic():
            ultima = self._obtener_ultima_version()
            nueva_version = ultima.version + 1 if ultima else 1
            self._desactivar_activas()
            self.archivo_webp = self._convertir_webp()
            nueva = self._crear_nueva_version(nueva_version)
            self._crear_miniatura(nueva)
        return nueva    

        
    
    def desactivar(self):
        with transaction.atomic():
            activa = ImagenAlmacen.objects.filter(
                app=self.data["app"],
                origen_tipo=self.data["origen_tipo"],
                origen_id=self.data["origen_id"],
                paciente_tipo=self.data["paciente_tipo"],
                paciente_id=self.data["paciente_id"],
                activo=True
            ).select_for_update().first()

            if not activa:
                raise ValidationError({"error": "No existe imagen activa."})

            activa.desactivar(self.data.get("usuario_snapshot"))

            return activa

    def _obtener_ultima_version(self):
        return ImagenAlmacen.objects.filter(
            app=self.data["app"],
            origen_tipo=self.data["origen_tipo"],
            origen_id=self.data["origen_id"],
            paciente_tipo=self.data["paciente_tipo"],
            paciente_id=self.data["paciente_id"]
        ).order_by("-version").first()
    

    def _desactivar_activas(self):
        ImagenAlmacen.objects.filter(
            app=self.data["app"],
            origen_tipo=self.data["origen_tipo"],
            origen_id=self.data["origen_id"],
            paciente_tipo=self.data["paciente_tipo"],
            paciente_id=self.data["paciente_id"],
            activo=True
        ).update(
            activo=False,
            fecha_reemplazo=timezone.now(),
            usuario_desactivador=self.data.get("usuario_snapshot")
        )


    def _crear_nueva_version(self, version):
        archivo = self.archivo_webp
        return ImagenAlmacen.objects.create(
            app=self.data["app"],
            origen_tipo=self.data["origen_tipo"],
            origen_id=self.data["origen_id"],
            paciente_tipo=self.data["paciente_tipo"],
            paciente_id=self.data["paciente_id"],
            archivo=archivo,
            tipo_imagen=self.data["tipo_imagen"],
            tamaño=archivo.size,
            formato=archivo.name.split('.')[-1],
            version=version,
            usuario_creador=self.data.get("usuario_snapshot"),
            activo=True
        )
    
    

    def _convertir_webp(self):
        archivo = self.data["archivo"]

        if archivo.content_type == "image/webp":
            return archivo 
        return convertir_a_webp(archivo)
    
    def _crear_miniatura(self, imagen):
        miniatura = generar_miniatura(self.archivo_webp)

        imagen.miniatura.save(
            f"thumb_{imagen.uuid}.webp",
            miniatura,
            save=True
        )
