import os
import mimetypes
import cloudinary.utils
from django.http import HttpResponseNotFound, FileResponse, HttpResponseRedirect
from django.conf import settings
from django.views.decorators.http import require_GET


@require_GET
def serve_media_view(request, path):
    """
    Directs media requests to Cloudinary CDN or local files with full HTTP 206 streaming.
    """
    safe_path = os.path.normpath(path).lstrip('/\\')
    full_path = os.path.join(settings.MEDIA_ROOT, safe_path)

    # 1. If file exists on local disk (e.g. dev mode), stream directly
    if os.path.exists(full_path):
        if not os.path.abspath(full_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
            return HttpResponseNotFound("Invalid media path.")
        content_type, _ = mimetypes.guess_type(full_path)
        content_type = content_type or 'application/octet-stream'
        response = FileResponse(open(full_path, 'rb'), content_type=content_type)
        response['Accept-Ranges'] = 'bytes'
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    # 2. Seamlessly redirect to Cloudinary CDN URL
    clean_path = safe_path.replace('\\', '/')
    folder, fname = os.path.split(clean_path)
    pub_id = f"zyra/{folder}/{os.path.splitext(fname)[0]}" if folder else f"zyra/{os.path.splitext(fname)[0]}"
    
    ext = os.path.splitext(fname)[1].lower()
    resource_type = 'video' if ext in ('.mp4', '.mov', '.webm', '.avi', '.m4v', '.mp3', '.wav', '.m4a') else 'image'
    
    c_url = cloudinary.utils.cloudinary_url(pub_id, resource_type=resource_type, secure=True)[0]
    return HttpResponseRedirect(c_url)
