from api_images.constants import (
    APP_VALIDAS,
    MAX_PIXELES_IMAGEN,
    MAX_TAMANO_IMAGEN_MB,
    ORIGEN_VALIDOS,
    TIPOS_PERMITIDOS,
)
from django.core.exceptions import ValidationError
from PIL import Image

def validar_imagen(archivo):
    if archivo.size > MAX_TAMANO_IMAGEN_MB * 1024 * 1024:
        raise ValidationError(
            f"La imagen supera los {MAX_TAMANO_IMAGEN_MB}MB permitidos"
        )

    if archivo.content_type not in TIPOS_PERMITIDOS:
        raise ValidationError("Formato de imagen no permitido")

    try:
        with Image.open(archivo) as img:
            formato_real = (img.format or "").upper()
            cantidad_pixeles = img.width * img.height
            if cantidad_pixeles > MAX_PIXELES_IMAGEN:
                raise ValidationError(
                    "La imagen supera la resolucion maxima permitida"
                )
            img.verify()
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(
            "El archivo está corrupto o no es una imagen válida"
        ) from exc
    finally:
        archivo.seek(0)

    # El nombre y el Content-Type los controla el cliente. Pillow confirma el
    # formato real para impedir guardar PNG/JPEG renombrados como .webp.
    if formato_real != "WEBP":
        raise ValidationError("El contenido de la imagen debe ser WebP")

def validar_app(value):
    if value not in APP_VALIDAS:
        raise ValidationError("app inválida")
    return value


def validar_origen_tipo(value):
    if value not in ORIGEN_VALIDOS:
        raise ValidationError("origen_tipo inválido")
    return value
