import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


class Command(BaseCommand):
    help = 'Scans local MEDIA_ROOT and uploads any media files to the configured object storage backend.'

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

                    if not default_storage.exists(rel_path):
                        default_storage.save(rel_path, ContentFile(file_bytes))
                        self.stdout.write(self.style.SUCCESS(f"Uploaded to storage: {rel_path} ({len(file_bytes)} bytes)"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Already in storage: {rel_path}"))

                    synced_count += 1
                    total_bytes += len(file_bytes)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to sync {rel_path}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Successfully synced {synced_count} media file(s) ({total_bytes / (1024 * 1024):.2f} MB) to object storage!"
        ))
