import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(PROJECT_ROOT))

# django < 1.3
CACHE_BACKEND = 'cache_utils.group_backend://localhost:11211/' #?timeout=60

# django 1.3+
CACHES = {
    'default': {
        'BACKEND': 'cache_utils.group_backend.CacheClass',
        'LOCATION': '127.0.0.1:11211',
    },
}

SECRET_KEY="asdf"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  
    }
}
  
INSTALLED_APPS = (
    'cache_utils',
)
