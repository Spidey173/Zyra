import os
import mimetypes
import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Post, Story, UserProfile, Message, Conversation


class Command(BaseCommand):
    help = 'Uploads local media files to Cloudinary and ensures cloud delivery.'

    def handle(self, *args, **options):
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') or os.environ.get('CLOUDINARY_CLOUD_NAME', '')
        api_key = getattr(settings, 'CLOUDINARY_API_KEY', '') or os.environ.get('CLOUDINARY_API_KEY', '')
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '') or os.environ.get('CLOUDINARY_API_SECRET', '')

        if not (cloud_name and api_key and api_secret):
            self.stdout.write(self.style.ERROR("Cloudinary credentials are not configured in environment."))
            return

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        self.stdout.write(self.style.NOTICE("Starting Cloudinary sync for local Zyra media..."))

        # Sync local media files if present
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            self.stdout.write(self.style.WARNING(f"MEDIA_ROOT '{media_root}' does not exist."))
            return

        synced_count = 0
        for root, _, files in os.walk(media_root):
            for filename in files:
                if filename.startswith('.'):
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, media_root).replace('\\', '/').lstrip('/')
                ext = os.path.splitext(filename)[1].lower()
                resource_type = 'video' if ext in ('.mp4', '.mov', '.webm', '.avi', '.m4v', '.mp3', '.wav', '.m4a') else 'image'
                folder, fname = os.path.split(rel_path)
                pub_id = f"zyra/{folder}/{os.path.splitext(fname)[0]}" if folder else f"zyra/{os.path.splitext(fname)[0]}"
                
                try:
                    with open(full_path, 'rb') as f:
                        res = cloudinary.uploader.upload(
                            f,
                            public_id=pub_id,
                            resource_type=resource_type,
                            overwrite=True
                        )
                        self.stdout.write(self.style.SUCCESS(f"Uploaded local file {rel_path} -> {res.get('secure_url')}"))
                        synced_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error uploading local {rel_path}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Cloudinary sync completed! {synced_count} file(s) synced."))
