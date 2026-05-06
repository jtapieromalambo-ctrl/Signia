web: gunicorn Signia.wsgi --bind 0.0.0.0:${PORT:-8000} --log-file -
release: python manage.py migrate
