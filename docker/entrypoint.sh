#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Attente de la base de données PostgreSQL..."

python << END
import sys
import time
import psycopg2
import os

dbname = os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB", "logos_db")
user = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER", "logos_user")
password = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD", "logos_password")
host = os.environ.get("DB_HOST", "db")
port = os.environ.get("DB_PORT", "5432")

attempts = 0
max_attempts = 30

while attempts < max_attempts:
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        print("PostgreSQL est prêt !")
        sys.exit(0)
    except psycopg2.OperationalError as e:
        print(f"PostgreSQL n'est pas prêt ({attempts}/{max_attempts}). Réessai dans 1s...")
        time.sleep(1)
        attempts += 1

print("Erreur: Impossible de se connecter à PostgreSQL")
sys.exit(1)
END

echo "Exécution des migrations Django..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "Démarrage de Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
