from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os


def convertir_a_webp(archivo, quality=85):
    archivo.seek(0)

    img = Image.open(archivo).convert("RGB")

    buffer = BytesIO()
    img.save(buffer, format="WEBP", quality=quality)

    archivo_webp = ContentFile(buffer.getvalue())
    archivo_webp.name = f"{archivo.name.split('.')[0]}.webp"

    return archivo_webp

def generar_miniatura(imagen_field, tamaño=(300, 300)):
    """Genera una miniatura a partir de un campo de imagen."""
    img = Image.open(imagen_field)
    img = img.convert("RGB")
    img.thumbnail(tamaño)

    buffer = BytesIO()
    img.save(buffer, format='WEBP', quality=70)
    return ContentFile(buffer.getvalue())


def eliminar_archivos_imagen(imagen_instance):
    """
    Elimina los archivos físicos (imagen principal y miniatura) 
    del sistema de archivos.
    """
    archivos_eliminados = []
    
    # Eliminar archivo principal
    if imagen_instance.archivo:
        if os.path.isfile(imagen_instance.archivo.path):
            os.remove(imagen_instance.archivo.path)
            archivos_eliminados.append("archivo")
    
    # Eliminar miniatura
    if imagen_instance.miniatura:
        if os.path.isfile(imagen_instance.miniatura.path):
            os.remove(imagen_instance.miniatura.path)
            archivos_eliminados.append("miniatura")
    
    return archivos_eliminados


def regenerar_miniatura(imagen_instance, nuevo_archivo):
    """
    Regenera la miniatura cuando se actualiza la imagen principal.
    Elimina la miniatura anterior si existe.
    """
    # Eliminar miniatura anterior si existe
    if imagen_instance.miniatura:
        if os.path.isfile(imagen_instance.miniatura.path):
            os.remove(imagen_instance.miniatura.path)
    
    # Generar nueva miniatura
    miniatura = generar_miniatura(nuevo_archivo)
    imagen_instance.miniatura.save(
        f"thumb_{imagen_instance.uuid}.jpg", 
        miniatura, 
        save=True
    )
    return imagen_instance.miniatura
