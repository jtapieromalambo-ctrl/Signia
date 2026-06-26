from django.core.management.base import BaseCommand
from usuarios.models import MensajeContacto


class Command(BaseCommand):
    help = 'Verifica el estado de los mensajes de contacto en la base de datos'

    def handle(self, *args, **options):
        total = MensajeContacto.objects.count()
        self.stdout.write(f'\nMensajes de contacto en la base de datos: {total}')

        if total == 0:
            self.stdout.write(self.style.WARNING('La tabla está vacía — nadie ha enviado mensajes aún.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Hay {total} mensaje(s):'))
            for msg in MensajeContacto.objects.order_by('-fecha')[:10]:
                self.stdout.write(f'  [{msg.fecha.strftime("%d/%m/%Y %H:%M")}] {msg.nombre} <{msg.correo}>')
