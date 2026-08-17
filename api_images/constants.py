MAX_TAMANO_IMAGEN_MB = 15
# Limita imagenes comprimidas con dimensiones desproporcionadas. El limite
# permite estudios de alta resolucion sin exponer el servidor a agotar memoria.
MAX_PIXELES_IMAGEN = 40_000_000
TIPOS_PERMITIDOS = ["image/webp"]
ORIGEN_VALIDOS = ["EVALUACIONRXDETALLE", "REFERENCIA", "RESPUESTA"]
APP_VALIDAS = ["RX", "REFERENCIA"]
ESPACIO_TOTAL_ASIGNADO_BYTES = int(1.5 * 1024**4)  # 1.5 TB
