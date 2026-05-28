import os
import sys

# Add 'apps' folder to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
apps_dir = os.path.join(current_dir, 'apps')
if apps_dir not in sys.path:
    sys.path.insert(0, apps_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
