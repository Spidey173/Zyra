from django.db import migrations
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

def migrate_persistent_media_forward(apps, schema_editor):
    """
    Copies any binary files stored in PersistentMediaFile table out to the
    configured default object storage before the model is removed.
    """
    db_alias = schema_editor.connection.alias
    tables = schema_editor.connection.introspection.table_names()
    if 'core_persistentmediafile' not in tables:
        return

    try:
        PersistentMediaFile = apps.get_model('core', 'PersistentMediaFile')
    except LookupError:
        return

    for pmf in PersistentMediaFile.objects.using(db_alias).all():
        clean_path = str(pmf.file_path).replace('\\', '/').lstrip('/')
        if pmf.data and clean_path:
            try:
                file_bytes = bytes(pmf.data) if isinstance(pmf.data, (bytes, memoryview, bytearray)) else pmf.data
                if not default_storage.exists(clean_path):
                    default_storage.save(clean_path, ContentFile(file_bytes))
            except Exception:
                # Do not block migration if storage provider is temporarily unreachable
                pass

def migrate_persistent_media_reverse(apps, schema_editor):
    # Reverse operation: PersistentMediaFile table is empty or deleted; no-op.
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_conversation_custom_theme_image_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_persistent_media_forward,
            reverse_code=migrate_persistent_media_reverse
        ),
    ]

