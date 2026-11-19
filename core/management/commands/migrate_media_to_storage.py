import os
import mimetypes
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection


class Command(BaseCommand):
    help = 'Safely migrates any existing media binary data from PostgreSQL (PersistentMediaFile) to the configured object storage backend.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Checking for legacy PersistentMediaFile data in PostgreSQL..."))

        # Inspect if table core_persistentmediafile exists in database
        tables = connection.introspection.table_names()
        if 'core_persistentmediafile' not in tables:
            self.stdout.write(self.style.SUCCESS("No legacy 'core_persistentmediafile' table found. Nothing to migrate."))
            return

        with connection.cursor() as cursor:
            cursor.execute("SELECT file_path, content_type, data, size FROM core_persistentmediafile")
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write(self.style.SUCCESS("Table 'core_persistentmediafile' is empty. No files to migrate."))
            return

        self.stdout.write(f"Found {len(rows)} file(s) in Postgres to migrate to object storage...")
        migrated_count = 0
        total_bytes = 0

        for row in rows:
            file_path, content_type, data, size = row
            if not file_path or not data:
                continue

            clean_path = str(file_path).replace('\\', '/').lstrip('/')
            try:
                # Convert memoryview / bytes to python bytes
                file_bytes = bytes(data) if isinstance(data, (bytes, memoryview, bytearray)) else data
                
                # Check if file already exists in default_storage
                if not default_storage.exists(clean_path):
                    saved_name = default_storage.save(clean_path, ContentFile(file_bytes))
                    self.stdout.write(self.style.SUCCESS(f"Migrated: {clean_path} -> {saved_name} ({len(file_bytes)} bytes)"))
                else:
                    self.stdout.write(self.style.WARNING(f"Already in storage: {clean_path}"))

                migrated_count += 1
                total_bytes += len(file_bytes)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to migrate {clean_path}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Successfully migrated {migrated_count} media file(s) ({total_bytes / (1024 * 1024):.2f} MB) to object storage!"
        ))

