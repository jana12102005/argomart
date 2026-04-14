import os
from pathlib import Path
import urllib.parse

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get(
        'SECRET_KEY',
        'agromart-dev-secret-key-change-in-production'
    )

    # =========================
    # DATABASE (PRIMARY: DATABASE_URL)
    # =========================
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        url = urllib.parse.urlparse(DATABASE_URL)

        MYSQL_HOST = url.hostname.strip()
        MYSQL_PORT = url.port or 3306
        MYSQL_USER = url.username
        MYSQL_PASSWORD = url.password
        MYSQL_DATABASE = url.path.lstrip("/").strip()

        # SSL required for Aiven
        MYSQL_SSL = {"ssl": {}}

    else:
        # =========================
        # FALLBACK (LOCAL / DEFAULT)
        # =========================
        MYSQL_HOST = os.environ.get(
            'MYSQL_HOST',
            'agromart-newstarinfosis-bf62.e.aivencloud.com'
        )

        MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 28554))

        MYSQL_USER = os.environ.get(
            'MYSQL_USER',
            'avnadmin'
        )

        MYSQL_PASSWORD = os.environ.get(
            'MYSQL_PASSWORD' )

        MYSQL_DATABASE = os.environ.get(
            'MYSQL_DATABASE',
            'defaultdb'
        )

        MYSQL_SSL = {"ssl": {}}

    # =========================
    # FILE SETTINGS
    # =========================
    UPLOAD_FOLDER = BASE_DIR / 'uploads' / 'bills'
    UPLOAD_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

    # =========================
    # APP SETTINGS
    # =========================
    LOW_STOCK_THRESHOLD = 10