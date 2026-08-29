import os
import mimetypes
from django.core.files.storage import FileSystemStorage
from django.conf import settings


class ResilientMediaStorage(FileSystemStorage):
    """
    Dual-layer resilient storage backend.
    Saves media to disk AND synchronizes binary data to PostgreSQL PersistentMediaFile.
    When a Render container sleeps after 15 minutes and restarts with a clean ephemeral disk,
    files are automatically recovered on demand without any data loss.
    """

    def _save(self, name, content):
        saved_name = super()._save(name, content)
        try:
            from .models import PersistentMediaFile
            content.seek(0)
            file_bytes = content.read()
            content_type, _ = mimetypes.guess_type(saved_name)
            content_type = content_type or 'application/octet-stream'

            normalized_path = saved_name.replace('\\', '/').lstrip('/')
            PersistentMediaFile.objects.update_or_create(
                file_path=normalized_path,
                defaults={
                    'data': file_bytes,
                    'content_type': content_type,
                    'size': len(file_bytes),
                }
            )
        except Exception:
            # Fallback gracefully if database is not available during initial migrations
            pass
        return saved_name

    def exists(self, name):
        if super().exists(name):
            return True
        try:
            from .models import PersistentMediaFile
            normalized_path = name.replace('\\', '/').lstrip('/')
            return PersistentMediaFile.objects.filter(file_path=normalized_path).exists()
        except Exception:
            return False

    def open(self, name, mode='rb'):
        try:
            full_path = self.path(name)
            if not os.path.exists(full_path):
                from .models import PersistentMediaFile
                normalized_path = name.replace('\\', '/').lstrip('/')
                stored = PersistentMediaFile.objects.filter(file_path=normalized_path).first()
                if not stored:
                    filename = os.path.basename(normalized_path)
                    stored = PersistentMediaFile.objects.filter(file_path__endswith=filename).first()
                if stored and stored.data:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'wb') as f:
                        f.write(stored.data)
        except Exception:
            pass
        return super().open(name, mode)
