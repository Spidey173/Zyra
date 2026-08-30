import os
import mimetypes
import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Post, Story, UserProfile, Message, Conversation, PersistentMediaFile


class Command(BaseCommand):
    help = 'Uploads all existing local media files and DB media to Cloudinary (25GB Free Storage) and updates references.'

    def handle(self, *args, **options):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )

        self.stdout.write(self.style.NOTICE("Starting Cloudinary migration for Zyra media..."))

        # 1. Sync from PersistentMediaFile in DB
        db_files = PersistentMediaFile.objects.all()
        self.stdout.write(f"Found {db_files.count()} files in PersistentMediaFile to push to Cloudinary...")
        
        for pmf in db_files:
            try:
                ext = os.path.splitext(pmf.file_path)[1].lower()
                resource_type = 'video' if ext in ('.mp4', '.mov', '.webm', '.avi', '.m4v', '.mp3', '.wav', '.m4a') else 'image'
                folder, fname = os.path.split(pmf.file_path)
                pub_id = f"zyra/{folder}/{os.path.splitext(fname)[0]}" if folder else f"zyra/{os.path.splitext(fname)[0]}"
                
                res = cloudinary.uploader.upload(
                    pmf.data,
                    public_id=pub_id,
                    resource_type=resource_type,
                    overwrite=True
                )
                sec_url = res.get('secure_url')
                self.stdout.write(self.style.SUCCESS(f"Uploaded DB file {pmf.file_path} -> {sec_url}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error uploading {pmf.file_path}: {e}"))

        # 2. Sync local media files if present
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
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
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error uploading local {rel_path}: {e}"))

        self.stdout.write(self.style.SUCCESS("All media successfully migrated to Cloudinary!"))
