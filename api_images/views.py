from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError
import uuid
import os
from api_images.models import (
    ImagenAlmacen,
    ImagenDispositivo,
    ImagenUsuario,
)
from api_images.utils.main import eliminar_archivos_imagen, regenerar_miniatura
from api_images.utils.logger import log_info, log_error, log_warning
from api_images.services.image_service import ImagenService, ImagenUsuarioService
from api_images.services.device_image_service import (
    ImagenDispositivoService,
)
from api_images.serializers import (
    ImagenAlmacenSerializer,
    SubirImagenDispositivoSerializer,
    BuscarImagenesSerializer,
    SubirImagenSerializer,
    SubirImagenUsuarioSerializer,
    BuscarImagenesUsuarioSerializer,
    IdentificarImagenSerializer,
    DesactivarImagenSerializer,
    DesactivarImagenesBatchSerializer,
    CambiarReferenciaImagenesSerializer,
)
from api_images.models import TipoPaciente
from api_images.constants import ESPACIO_TOTAL_ASIGNADO_BYTES
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Sum, Count
import time


# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def saludo(request):
    return Response({"saludo": "Hola, accediste con token válido"})



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subir_imagen(request):
    start = time.time()
    
    try:

        serializer = SubirImagenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = ImagenService(serializer.validated_data)
        imagen = service.sincronizar()

        
        elapsed = time.time() - start
        log_info(
            f"Imagen subida correctamente "
            f"app={imagen.app} "
            f"uuid={imagen.uuid} "
            f"tipo={imagen.tipo_imagen} "
            f"version={imagen.version} "
            f"tiempo={elapsed:.2f}s"
        )

        return Response({
            "uuid": str(imagen.uuid),
            "version": imagen.version
        }, status=201)

    except ValidationError as e:
        log_error(
            f"Validación fallida en subir_imagen "
            f"error={e.detail}"
        )

        return Response(
            {"error": e.detail},
            status=400
        )

    except IntegrityError:
        log_error(f"Intento duplicado de imagen activa ")

        return Response(
            {"error": "Ya existe una imagen activa para este origen."},
            status=400
        )

    except Exception as e:
        log_error(f"Error interno en subir_imagen")

        return Response(
            {"error": "Error interno procesando la imagen."},

            status=500
        )
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subir_imagen_usuario(request):
    start = time.time()
    
    try:
        serializer = SubirImagenUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ImagenUsuarioService(serializer.validated_data)
        imagen = service.guardar()
        imagen.refresh_from_db()

        elapsed = time.time() - start
        log_info(
            f"Imagen subida correctamente "
            f"usuario_id={imagen.user_id} "
            f"tiempo={elapsed:.2f}s"
        )

        return Response({
            "uuid": imagen.uuid,
            "url": f"{settings.MEDIA_URL}{imagen.imagen}",
        }, status=201)

    except ValidationError as e:
        log_error(
            f"Validación fallida en subir_imagen "
            f"error={e.detail}"
        )

        return Response(
            {"error": e.detail},
            status=400
        )

    except IntegrityError:
        log_error(f"Intento duplicado de imagen activa ")

        return Response(
            {"error": "Ya existe una imagen activa para este origen."},
            status=400
        )

    except Exception as e:
        log_error(f"Error interno en subir_imagen")

        return Response(
            {"error": "Error interno procesando la imagen."},

            status=500
        )
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buscar_imagenes_usuario(request):

    try:
        serializer = BuscarImagenesUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuarios_ids = serializer.validated_data["usuarios_ids"]

        imagenes = ImagenUsuario.objects.filter(
            user_id__in=usuarios_ids
        ).values(
            "user_id",
            "uuid",
            "imagen"
        )

        resultados = [
            {
                "usuario_id": img["user_id"],
                "uuid": img["uuid"],
                "url": f"{settings.MEDIA_URL}{img['imagen']}" if img["imagen"] else None,
            }
            for img in imagenes
        ]

        return Response(resultados, status=200)

    except Exception as e:

        log_error(f"Error interno en buscar_imagenes_usuario {e}")

        return Response(
            {"error": "Error interno al consultar imagenes de usuario"},
            status=500
        )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def desactivar_imagen(request):
    start = time.time()
        
    try:
        serializer = DesactivarImagenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ImagenService(serializer.validated_data)
        imagen= service.desactivar()

        elapsed = time.time() - start

        log_info(
            f"Imagen desactivada "
            f"imagen_id={imagen.uuid} "
            f"tiempo={elapsed:.2f}s"
        )

        return Response(
            {"mensaje": "Imagen desactivada correctamente."},
            status=200
        )
    
    except ValidationError as e:
        log_warning(
            f"Validación fallida desactivar_imagen "
            f"error={e.detail}"
        )
        return Response(
            {"error": str(e)},
            status=400
        )

    except Exception:
        log_error("Error interno desactivando imagen")

        return Response(
            {"error": "Error interno desactivando imagen."},
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buscar_imagenes(request):

    try:
        serializer = BuscarImagenesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        imagenes = ImagenAlmacen.objects.filter(
            app=data["app"],
            origen_tipo=data["origen_tipo"],
            origen_id__in=data["origen_ids"],
            paciente_tipo=data["paciente_tipo"],
            paciente_id=data["paciente_id"],
            activo=True
        ).values(
            "origen_id",
            "uuid",
            "archivo",
            "miniatura",
            "tipo_imagen"
        )

        resultados = [
            {
                "origen_id": img["origen_id"],
                "uuid": img["uuid"],
                "url": f"{settings.MEDIA_URL}{img['archivo']}",
                "miniatura": f"{settings.MEDIA_URL}{img['miniatura']}" if img["miniatura"] else None,
                "tipo_imagen": img["tipo_imagen"]
            }
            for img in imagenes
        ]

        return Response(resultados, status=200)

    except Exception as e:

        log_error(f"Error interno en buscar_imagenes {e}")

        return Response(
            {"error": "Error interno al consultar imágenes"},
            status=500
        )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def desactivar_imagenes_batch(request):

    start = time.time()

    try:
        serializer = DesactivarImagenesBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        actualizados = ImagenAlmacen.objects.filter(
            app=data["app"],
            origen_tipo=data["origen_tipo"],
            paciente_id=data["paciente_id"],
            paciente_tipo=data["paciente_tipo"],
            origen_id__in=data["origen_ids"],
            activo=True
        ).update(
            activo=False,
            usuario_desactivador=data["usuario_snapshot"]
        )

        elapsed = time.time() - start

        log_info(
            f"Desactivacion batch completada "
            f"app={data['app']} "
            f"origen_tipo={data['origen_tipo']} "
            f"paciente_id={data['paciente_id']} "
            f"cantidad={actualizados} "
            f"tiempo={elapsed:.2f}s"
        )

        return Response({
            "ok": True,
            "desactivadas": actualizados
        }, status=200)

    except Exception:

        log_error("Error interno en desactivar_imagenes_batch")

        return Response(
            {"error": "Error interno desactivando imágenes."},
            status=500
        )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def migrar_imagenes_externo_a_interno(request):

    start = time.time()

    try:
        serializer = CambiarReferenciaImagenesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            actualizados = ImagenAlmacen.objects.filter(
                paciente_id=data["paciente_externo_id"],
                paciente_tipo=TipoPaciente.EXTERNO
            ).update(
                paciente_id=data["paciente_interno_id"],
                paciente_tipo=TipoPaciente.INTERNO
            )

        elapsed = time.time() - start

        log_info(
            f"Migracion externo->interno completada "
            f"externo_id={data['paciente_externo_id']} "
            f"interno_id={data['paciente_interno_id']} "
            f"cantidad={actualizados} "
            f"tiempo={elapsed:.2f}s"
        )

        return Response({
            "ok": True,
            "convertidas": actualizados
        }, status=200)

    except Exception:

        log_error("Error en migrar_imagenes_externo_a_interno")

        return Response(
            {"error": "Error interno cambiando referencia de imágenes."},
            status=500
        )

# //////////////////////

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_imagen(request):
    """
    Elimina una imagen identificándola por los campos:
    app, origen_tipo, origen_id, paciente_id, tipo_imagen (en el body).
    También elimina los archivos físicos asociados (imagen y miniatura).
    """
    serializer = IdentificarImagenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        imagen = ImagenAlmacen.objects.get(
            app=data["app"],
            origen_tipo=data["origen_tipo"],
            origen_id=data["origen_id"],
            paciente_id=data["paciente_id"],
            tipo_imagen=data["tipo_imagen"],
            activo=True,
        )
    except ImagenAlmacen.DoesNotExist:
        return Response({"error": "Imagen no encontrada"}, status=404)
    
    # Guardar info antes de eliminar
    uuid_eliminado = str(imagen.uuid)
    
    # Eliminar archivos físicos
    archivos_eliminados = eliminar_archivos_imagen(imagen)
    
    # Eliminar registro de la base de datos
    imagen.delete()
    
    return Response({
        "mensaje": "Imagen eliminada correctamente",
        "uuid": uuid_eliminado,
        "archivos_eliminados": archivos_eliminados
    }, status=200)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modificar_imagen(request):
    """
    Modifica una imagen existente identificándola por los campos:
    app, origen_tipo, origen_id, paciente_id, tipo_imagen (en el body).
    PUT: Requiere todos los campos
    PATCH: Solo los campos a modificar
    
    Si se envía una nueva imagen, se reemplaza la anterior y se regenera la miniatura.
    """
    serializer = IdentificarImagenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        imagen = ImagenAlmacen.objects.get(
            app=data["app"],
            origen_tipo=data["origen_tipo"],
            origen_id=data["origen_id"],
            paciente_id=data["paciente_id"],
            tipo_imagen=data["tipo_imagen"],
            activo=True,
        )
    except ImagenAlmacen.DoesNotExist:
        return Response({"error": "Imagen no encontrada"}, status=404)
    
    nuevo_archivo = request.FILES.get("imagen")
    update_data = request.data.copy()
    
    # Si hay nuevo archivo, procesar
    if nuevo_archivo:
        # Validar tamaño
        if nuevo_archivo.size > 10 * 1024 * 1024:
            return Response({"error": "Imagen supera el tamaño permitido"}, status=400)
        
        # Eliminar archivo anterior
        if imagen.archivo:
            if os.path.isfile(imagen.archivo.path):
                os.remove(imagen.archivo.path)
        
        update_data["archivo"] = nuevo_archivo
        update_data["tamaño"] = nuevo_archivo.size
        update_data["formato"] = nuevo_archivo.content_type
    
    partial = request.method == 'PATCH'
    serializer = ImagenAlmacenSerializer(imagen, data=update_data, partial=partial)
    
    if serializer.is_valid():
        imagen_actualizada = serializer.save()
        
        # Si se subió nueva imagen, regenerar miniatura
        if nuevo_archivo:
            regenerar_miniatura(imagen_actualizada, imagen_actualizada.archivo)
        
        return Response({
            "uuid": str(imagen_actualizada.uuid),
            "url": imagen_actualizada.archivo.url,
            "miniatura": imagen_actualizada.miniatura.url if imagen_actualizada.miniatura else None,
            "mensaje": "Imagen modificada correctamente"
        }, status=200)
    
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estadisticas_almacenamiento(request):
    """
    Devuelve estadísticas de almacenamiento para el dashboard:
    - Espacio total asignado (1.5 TB)
    - Consumo por app y general
    - Espacio libre
    - Cantidad de imágenes por app y total
    """
    espacio_total = ESPACIO_TOTAL_ASIGNADO_BYTES

    # Estadísticas por app
    por_app = (
        ImagenAlmacen.objects.filter(activo=True)
        .values("app")
        .annotate(
            consumido_bytes=Sum("tamaño"),
            cantidad_imagenes=Count("uuid"),
        )
        .order_by("app")
    )

    apps = []
    consumido_total = 0
    imagenes_total = 0
    for item in por_app:
        consumido = item["consumido_bytes"] or 0
        cantidad = item["cantidad_imagenes"] or 0
        consumido_total += consumido
        imagenes_total += cantidad
        apps.append({
            "app": item["app"],
            "consumido_bytes": consumido,
            "consumido_mb": round(consumido / (1024 ** 2), 2),
            "consumido_gb": round(consumido / (1024 ** 3), 2),
            "cantidad_imagenes": cantidad,
        })

    espacio_libre = espacio_total - consumido_total

    return Response({
        "espacio_total_bytes": espacio_total,
        "espacio_total_gb": round(espacio_total / (1024 ** 3), 2),
        "espacio_total_tb": round(espacio_total / (1024 ** 4), 2),
        "consumido_total_bytes": consumido_total,
        "consumido_total_mb": round(consumido_total / (1024 ** 2), 2),
        "consumido_total_gb": round(consumido_total / (1024 ** 3), 2),
        "espacio_libre_bytes": espacio_libre,
        "espacio_libre_gb": round(espacio_libre / (1024 ** 3), 2),
        "espacio_libre_tb": round(espacio_libre / (1024 ** 4), 2),
        "imagenes_total": imagenes_total,
        "por_app": apps,
    }, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verificar_integridad(request):
    """
    Verifica la integridad entre archivos físicos y registros en la base de datos.
    
    Retorna:
    - registros_sin_archivo: registros activos en BD cuyo archivo no existe en disco.
    - archivos_sin_registro: archivos en MEDIA_ROOT que no corresponden a ningún registro.
    """
    media_root = settings.MEDIA_ROOT

    # 1. Registros en BD cuyo archivo no existe físicamente
    registros_sin_archivo = []
    imagenes_activas = ImagenAlmacen.objects.filter(activo=True)

    # Guardar rutas de BD para comparar después
    rutas_en_bd = set()

    for img in imagenes_activas:
        try:
            ruta_archivo = img.archivo.path
            rutas_en_bd.add(ruta_archivo)
            if not os.path.isfile(ruta_archivo):
                registros_sin_archivo.append({
                    "uuid": str(img.uuid),
                    "app": img.app,
                    "origen_tipo": img.origen_tipo,
                    "origen_id": img.origen_id,
                    "paciente_id": img.paciente_id,
                    "tipo_imagen": img.tipo_imagen,
                    "ruta_esperada": ruta_archivo,
                })
        except Exception:
            registros_sin_archivo.append({
                "uuid": str(img.uuid),
                "app": img.app,
                "origen_tipo": img.origen_tipo,
                "origen_id": img.origen_id,
                "paciente_id": img.paciente_id,
                "tipo_imagen": img.tipo_imagen,
                "ruta_esperada": "(error al obtener ruta)",
            })

        # También agregar miniatura a las rutas de BD
        if img.miniatura:
            try:
                rutas_en_bd.add(img.miniatura.path)
            except Exception:
                pass

    # 2. Archivos en disco sin registro en BD
    archivos_sin_registro = []
    if os.path.isdir(media_root):
        for dirpath, dirnames, filenames in os.walk(media_root):
            for filename in filenames:
                ruta_completa = os.path.join(dirpath, filename)
                if ruta_completa not in rutas_en_bd:
                    ruta_relativa = os.path.relpath(ruta_completa, media_root)
                    archivos_sin_registro.append({
                        "ruta_completa": ruta_completa,
                        "ruta_relativa": ruta_relativa,
                    })

    return Response({
        "registros_sin_archivo": registros_sin_archivo,
        "cantidad_registros_sin_archivo": len(registros_sin_archivo),
        "archivos_sin_registro": archivos_sin_registro,
        "cantidad_archivos_sin_registro": len(archivos_sin_registro),
    }, status=200)


def _construir_respuesta_imagen_dispositivo(imagen):
    return {
        "uuid": str(imagen.uuid),
        "dispositivo_id": imagen.dispositivo_id,
        "url": f"{settings.MEDIA_URL}{imagen.archivo.name}",
        "miniatura": (
            f"{settings.MEDIA_URL}{imagen.miniatura.name}"
            if imagen.miniatura
            else None
        ),
        "tipo_imagen": imagen.tipo_imagen,
        "tamano": imagen.tamano,
        "formato": imagen.formato,
        "fecha_creado": imagen.fecha_creado,
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def subir_imagen_dispositivo(request):
    try:
        serializer = SubirImagenDispositivoSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        imagen = ImagenDispositivoService(
            serializer.validated_data,
        ).guardar()

        return Response(
            {
                "imagen": _construir_respuesta_imagen_dispositivo(
                    imagen,
                )
            },
            status=status.HTTP_201_CREATED,
        )

    except ValidationError as exc:
        log_warning(
            "Validacion fallida al subir imagen de equipo "
            f"error={exc.detail}"
        )
        return Response(
            {"error": exc.detail},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception:
        log_error("Error interno al subir imagen de equipo")
        return Response(
            {"error": "Error interno procesando la imagen del equipo."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def buscar_imagenes_dispositivo(request, dispositivo_id):
    if dispositivo_id < 1:
        return Response(
            {"error": "El dispositivo_id debe ser mayor que cero."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        imagenes = (
            ImagenDispositivo.objects
            .filter(dispositivo_id=dispositivo_id)
            .order_by("fecha_creado")
        )

        resultados = [
            _construir_respuesta_imagen_dispositivo(imagen)
            for imagen in imagenes
        ]

        return Response(
            {
                "dispositivo_id": dispositivo_id,
                "cantidad": len(resultados),
                "imagenes": resultados,
            },
            status=status.HTTP_200_OK,
        )

    except Exception:
        log_error("Error interno consultando imagenes de equipo")
        return Response(
            {"error": "Error interno consultando imagenes del equipo."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
