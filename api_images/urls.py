from django.urls import path
from api_images.views import (
    saludo, 
    subir_imagen, 
    subir_imagen_usuario,
    buscar_imagenes,
    buscar_imagenes_usuario,
    eliminar_imagen,
    modificar_imagen,
    estadisticas_almacenamiento,
    verificar_integridad,
    desactivar_imagen,
    desactivar_imagenes_batch,
    migrar_imagenes_externo_a_interno,
    subir_imagen_dispositivo,
    buscar_imagenes_dispositivo,

)


urlpatterns = [
    path("saludo/", saludo, name="saludo"),
    path("subir_imagen/", subir_imagen, name="subir_imagen"),
    path("subir_imagen_usuario/", subir_imagen_usuario, name="subir_imagen_usuario"),

    path("buscar/", buscar_imagenes, name="buscar_imagenes"),
    path("buscar_imagenes_usuarios/", buscar_imagenes_usuario, name="buscar_imagenes_usuarios"),

    path("desactivar/",desactivar_imagen , name="desactivar_imagen"),
    path("desactivar-batch/",desactivar_imagenes_batch , name="desactivar_imagen_batch"),
    path("migrar-imagenes-externo-a-interno/", migrar_imagenes_externo_a_interno, name="migrar_imagenes_externo_a_interno" ),


    path("eliminar/", eliminar_imagen, name="eliminar_imagen"),
    path("modificar/", modificar_imagen, name="modificar_imagen"),
    path("estadisticas/", estadisticas_almacenamiento, name="estadisticas_almacenamiento"),
    path("verificar_integridad/", verificar_integridad, name="verificar_integridad"),


    path(
        "equipos/subir/",
        subir_imagen_dispositivo,
        name="subir_imagen_dispositivo",
    ),
    path(
        "equipos/<int:dispositivo_id>/imagenes/",
        buscar_imagenes_dispositivo,
        name="buscar_imagenes_dispositivo",
    ),
]
