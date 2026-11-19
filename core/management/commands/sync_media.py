import os
import mimetypes
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import PersistentMediaFile


class Command(BaseCommand):
    help = 'Scans MEDIA_ROOT and uploads all local media files into PersistentMediaFile in PostgreSQL.'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            self.stdout.write(self.style.WARNING(f"MEDIA_ROOT '{media_root}' does not exist."))
            return

        synced_count = 0
        total_bytes = 0

        for root, _, files in os.walk(media_root):
            for filename in files:
                if filename.startswith('.'):
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, media_root).replace('\\', '/').lstrip('/')
                
                try:
                    with open(full_path, 'rb') as f:
                        file_bytes = f.read()

                    content_type, _ = mimetypes.guess_type(full_path)
                    content_type = content_type or 'application/octet-stream'

                    PersistentMediaFile.objects.update_or_create(
                        file_path=rel_path,
                        defaults={
                            'data': file_bytes,
                            'content_type': content_type,
                            'size': len(file_bytes),
                        }
                    )
                    synced_count += 1
                    total_bytes += len(file_bytes)
                    self.stdout.write(self.style.SUCCESS(f"Synced: {rel_path} ({len(file_bytes)} bytes)"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to sync {rel_path}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {synced_count} media files ({total_bytes / (1024*1024):.2f} MB) to database!"))
