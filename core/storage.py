import os
import mimetypes
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.conf import settings


@deconstructible
class CloudinaryMediaStorage(Storage):
    """
    Direct Cloudinary media storage backend for all user-generated media:
    - Posts (Photos & Video Reels)
    - Stories (Images, Videos, Music)
    - Profile Avatars & Wallpapers
    - Direct Message Voice Notes & Photos
    - Custom Chat Themes
    
    Provides 25GB free CDN storage and fast global streaming while preserving
    Neon PostgreSQL storage exclusively for message text and relational records.
    """

    def __init__(self, **kwargs):
        self.cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', 'dg04dd5o1')
        self.api_key = getattr(settings, 'CLOUDINARY_API_KEY', '549768947857682')
        self.api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', 'R2dzLnaTB_gIbCVcWF9ptUIVZN8')
        
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True
        )

    def _save(self, name, content):
        content.seek(0)
        ext = os.path.splitext(name)[1].lower()

        # Classify resource type for Cloudinary
        if ext in ('.mp4', '.mov', '.webm', '.avi', '.m4v', '.mkv'):
            resource_type = 'video'
        elif ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.bmp'):
            resource_type = 'image'
        elif ext in ('.mp3', '.wav', '.m4a', '.aac', '.ogg', '.weba'):
            resource_type = 'video'  # Cloudinary processes audio under 'video' resource type for streaming
        else:
            resource_type = 'auto'

        clean_name = name.replace('\\', '/').lstrip('/')
        folder, filename = os.path.split(clean_name)
        public_id_base, _ = os.path.splitext(filename)
        public_id = f"zyra/{folder}/{public_id_base}" if folder else f"zyra/{public_id_base}"

        try:
            cloudinary.uploader.upload(
                content,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
                unique_filename=False,
                use_filename=True
            )
            return clean_name
        except Exception as e:
            # Fallback to local file if upload fails
            local_path = os.path.join(settings.MEDIA_ROOT, clean_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            content.seek(0)
            with open(local_path, 'wb') as f:
                f.write(content.read())
            return clean_name

    def url(self, name):
        if not name:
            return ''
        name_str = str(name).replace('\\', '/').lstrip('/')
        if name_str.startswith('http://') or name_str.startswith('https://'):
            return name_str

        folder, filename = os.path.split(name_str)
        public_id_base, ext = os.path.splitext(filename)
        pub_id = f"zyra/{folder}/{public_id_base}" if folder else f"zyra/{public_id_base}"

        ext_lower = ext.lower()
        if ext_lower in ('.mp4', '.mov', '.webm', '.avi', '.m4v', '.mp3', '.wav', '.m4a', '.weba'):
            resource_type = 'video'
        elif ext_lower in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.bmp'):
            resource_type = 'image'
        else:
            resource_type = 'auto'

        return cloudinary.utils.cloudinary_url(pub_id, resource_type=resource_type, secure=True)[0]

    def exists(self, name):
        return False

    def get_available_name(self, name, max_length=None):
        return name

