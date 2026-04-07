from django.core.management.base import BaseCommand
from reconocimientos.models import VideoSeña
from reconocimientos.scripts.extract_landmarks import process_all_videos
import os


class Command(BaseCommand):
    help = 'Extrae landmarks de todos los videos no procesados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reprocesar todos los videos, incluso los ya procesados'
        )

    def handle(self, *args, **options):
        output_dir = os.path.join('reconocimientos', 'models', 'landmarks')

        if options['all']:
            queryset = VideoSeña.objects.all()
            self.stdout.write("Procesando TODOS los videos...")
        else:
            queryset = VideoSeña.objects.filter(procesado=False)
            self.stdout.write(f"Videos pendientes: {queryset.count()}")

        processed, errors = process_all_videos(queryset, output_dir)
        self.stdout.write(self.style.SUCCESS(f'Listo: {processed} procesados, {errors} errores'))