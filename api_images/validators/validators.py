from api_images.constants import MAX_TAMANO_IMAGEN_MB, TIPOS_PERMITIDOS, APP_VALIDAS, ORIGEN_VALIDOS
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
        img = Image.open(archivo)
        img.verify()
        archivo.seek(0) 
        
    except Exception:
        raise ValidationError("El archivo está corrupto o no es una imagen válida")


def validar_app(value):
    if value not in APP_VALIDAS:
        raise ValidationError("app inválida")
    return value


def validar_origen_tipo(value):
    if value not in ORIGEN_VALIDOS:
        raise ValidationError("origen_tipo inválido")
    return value
