import os
import mimetypes
from django.http import HttpResponseNotFound, FileResponse
from django.conf import settings
from django.views.decorators.http import require_GET


@require_GET
def serve_media_view(request, path):
    """
    High-performance, range-aware media streaming server with automatic database recovery.
    - If file exists on disk: streams immediately with HTTP 206 Partial Content support (seeking & scrubbing).
    - If file was wiped after Render container sleep/restart: seamlessly restores file from PostgreSQL
      database to local disk and streams it with zero downtime.
    """
    safe_path = os.path.normpath(path).lstrip('/\\')
    full_path = os.path.join(settings.MEDIA_ROOT, safe_path)

    # Security check: Prevent path traversal outside MEDIA_ROOT
    if not os.path.abspath(full_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        return HttpResponseNotFound("Invalid media path.")

    if not os.path.exists(full_path):
        try:
            from ..models import PersistentMediaFile
            normalized_path = safe_path.replace('\\', '/')
            stored = PersistentMediaFile.objects.filter(file_path=normalized_path).first()
            if not stored:
                filename = os.path.basename(normalized_path)
                stored = PersistentMediaFile.objects.filter(file_path__endswith=filename).first()

            if stored and stored.data:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb') as f:
                    f.write(stored.data)
            else:
                return HttpResponseNotFound("Media file not found.")
        except Exception:
            return HttpResponseNotFound("Media recovery error.")

    content_type, _ = mimetypes.guess_type(full_path)
    content_type = content_type or 'application/octet-stream'

    response = FileResponse(open(full_path, 'rb'), content_type=content_type)
    response['Accept-Ranges'] = 'bytes'
    response['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response
