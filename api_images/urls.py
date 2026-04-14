from django.urls import path
from api_images.views import (
    saludo, 
    subir_imagen, 
    buscar_imagenes,
    eliminar_imagen,
    modificar_imagen,
    estadisticas_almacenamiento,
    verificar_integridad,
    desactivar_imagen,
    desactivar_imagenes_batch,
    migrar_imagenes_externo_a_interno

)


urlpatterns = [
    path("saludo/", saludo, name="saludo"),
    path("subir_imagen/", subir_imagen, name="subir_imagen"),
    path("buscar/", buscar_imagenes, name="buscar_imagenes"),
    path("desactivar/",desactivar_imagen , name="desactivar_imagen"),
    path("desactivar-batch/",desactivar_imagenes_batch , name="desactivar_imagen_batch"),
    path("migrar-imagenes-externo-a-interno/", migrar_imagenes_externo_a_interno, name="migrar_imagenes_externo_a_interno" ),


    path("eliminar/", eliminar_imagen, name="eliminar_imagen"),
    path("modificar/", modificar_imagen, name="modificar_imagen"),
    path("estadisticas/", estadisticas_almacenamiento, name="estadisticas_almacenamiento"),
    path("verificar_integridad/", verificar_integridad, name="verificar_integridad"),
]