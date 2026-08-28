import os
import uuid
import datetime
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

@deconstructible
class UploadPath:
    """
    Deconstructible callable for upload_to to ensure seamless Django migrations.
    Formats paths as: <folder_name>/YYYY/MM/<uuid4>.<extension>
    """
    def __init__(self, folder_name):
        self.folder_name = folder_name

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1].lower() if '.' in filename else 'bin'
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        now = datetime.datetime.now()
        return os.path.join(self.folder_name, now.strftime('%Y'), now.strftime('%m'), unique_name)

    def __eq__(self, other):
        return isinstance(other, UploadPath) and self.folder_name == other.folder_name


def generate_upload_path(folder_name):
    """Helper returning a deconstructible UploadPath instance."""
    return UploadPath(folder_name)


def get_media_url(file_field, default_url=None):
    """
    Safely resolves media URL.
    - If empty, returns default_url or None.
    - If already an absolute http/https URL string, returns it directly.
    - Otherwise returns file_field.url safely.
    """
    if not file_field:
        return default_url
    
    val = str(file_field)
    if val.startswith('http://') or val.startswith('https://'):
        return val
    
    try:
        return file_field.url
    except Exception:
        return default_url


ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.avi', '.m4v'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}

def validate_media_file(file_obj, media_types=('image',), max_size_mb=50):
    """
    Validates uploaded file size and extension.
    Raises ValidationError if invalid.
    """
    if not file_obj:
        return True

    # Validate size
    max_bytes = max_size_mb * 1024 * 1024
    if hasattr(file_obj, 'size') and file_obj.size > max_bytes:
        raise ValidationError(f"File size exceeds maximum allowed limit of {max_size_mb} MB.")

    # Validate extension
    name = getattr(file_obj, 'name', '')
    ext = os.path.splitext(name)[1].lower() if name else ''
    allowed_exts = set()
    if 'image' in media_types:
        allowed_exts.update(ALLOWED_IMAGE_EXTENSIONS)
    if 'video' in media_types:
        allowed_exts.update(ALLOWED_VIDEO_EXTENSIONS)
    if 'audio' in media_types:
        allowed_exts.update(ALLOWED_AUDIO_EXTENSIONS)

    if ext and ext not in allowed_exts:
        raise ValidationError(f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(allowed_exts))}")

    return True


def compress_and_optimize_image(image_file, max_dimension=1600, quality=85):
    """
    Auto-orients EXIF, downscales photos exceeding max_dimension, and
    compresses image to progressive JPEG or WebP at 85% quality.
    Reduces 5MB-10MB mobile uploads down to ~150-250KB.
    """
    if not image_file:
        return image_file

    import io
    from PIL import Image, ImageOps
    from django.core.files.base import ContentFile

    try:
        image_file.seek(0)
        img = Image.open(image_file)

        # 1. Auto-orient based on EXIF
        img = ImageOps.exif_transpose(img)

        # 2. Resize if dimension > max_dimension
        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / max(w, h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 3. Determine save format & mode
        orig_format = (img.format or 'JPEG').upper()
        output_io = io.BytesIO()

        if orig_format in ('PNG', 'WEBP') and img.mode in ('RGBA', 'LA'):
            img.save(output_io, format='WEBP', quality=quality, optimize=True)
            ext = 'webp'
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_io, format='JPEG', quality=quality, optimize=True, progressive=True)
            ext = 'jpg'

        output_io.seek(0)
        base_name = os.path.splitext(getattr(image_file, 'name', 'upload'))[0]
        new_filename = f"{base_name}.{ext}"
        return ContentFile(output_io.getvalue(), name=new_filename)
    except Exception:
        # Fallback to original if Pillow cannot process
        try:
            image_file.seek(0)
        except Exception:
            pass
        return image_file

