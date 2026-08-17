"""Configuracion aislada para ejecutar la suite sin tocar MySQL ni media real."""

import os
import tempfile
from pathlib import Path


TEST_DATA_ROOT = Path(tempfile.gettempdir()) / "siwih-images-tests"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = (
    "solo-pruebas-no-usar-en-produccion-00000000000000000000"
)
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["DEBUG"] = "0"
os.environ["LOG_DIR"] = str(TEST_DATA_ROOT / "logs")
os.environ["MEDIA_ROOT"] = str(TEST_DATA_ROOT / "media")
os.environ["STATIC_ROOT"] = str(TEST_DATA_ROOT / "staticfiles")

from .settings import *  # noqa: F403,E402


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# La consola conserva los mensajes utiles y evita crear archivos durante CI.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "api_images": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
