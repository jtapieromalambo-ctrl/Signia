web: gunicorn Signia.wsgi --bind 0.0.0.0:$PORT --timeout 120 --log-file -
release: python manage.py collectstatic --noinput && python manage.py migrate && python manage.py setup_oauth
