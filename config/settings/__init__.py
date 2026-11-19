"""
Settings package for Zyra project.
Loads development or production settings based on DJANGO_ENV and DEBUG.
"""

from pathlib import Path
import os

# Load .env file first so environment variables are populated
BASE_DIR = Path(__file__).resolve().parent.parent.parent
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass
    try:
        with open(_env_path, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#'):
                    _key, _val = None, None
                    if '=' in _line:
                        _key, _val = _line.split('=', 1)
                    elif ':' in _line:
                        _key, _val = _line.split(':', 1)
                    if _key and _val is not None:
                        _key = _key.strip()
                        _val = _val.strip().strip('"\'')
                        if _key and _key not in os.environ:
                            os.environ[_key] = _val
    except Exception:
        pass

# Determine environment mode:
# 'production' / 'prod': Loads strict production settings
# 'development' / 'dev' / 'local': Loads development settings
env_mode = os.environ.get('DJANGO_ENV', '').lower().strip()
debug_mode = os.environ.get('DEBUG', 'False').lower().strip() in ('true', '1', 'yes')

if env_mode in ('prod', 'production') or (not env_mode and not debug_mode):
    from .prod import *
else:
    from .dev import *
