# Zyra — Production-Grade Social Media Platform

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Channels ASGI](https://img.shields.io/badge/ASGI-Django%20Channels%204.2-blueviolet?style=for-the-badge&logo=fastapi&logoColor=white)](https://channels.readthedocs.io/)
[![Redis](https://img.shields.io/badge/Redis-Channel%20Layer-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-ACID%20Compliant-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Object Storage](https://img.shields.io/badge/Storage-S3%20%2F%20R2%20%2F%20Cloudinary-orange?style=for-the-badge&logo=amazons3&logoColor=white)](https://django-storages.readthedocs.io/)
[![Tests](https://img.shields.io/badge/Tests-68%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/features/actions)

**A hardened, full-stack Instagram-inspired social platform built with Python, Django, ASGI Channels, Redis, PostgreSQL, and modular ES6 JavaScript.**

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Core Features](#-core-features)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [Quickstart: Local Development](#-quickstart-local-development)
- [Docker Setup](#-docker-setup)
- [Running the Test Suite](#-running-the-test-suite)
- [Environment Variables](#-environment-variables)
- [Deployment Guides](#-deployment-guides)
- [Screenshots](#-screenshots)
- [Key Design Decisions](#-key-design-decisions)
- [License](#-license)

---

## 📌 Overview

**Zyra** is an enterprise-hardened social platform engineered for high concurrency, real-time communication, and media delivery. Built using modern Django patterns, Zyra combines asynchronous protocol routing (ASGI) for WebSockets with a resilient relational database schema, modular frontend ES6 architecture, and decoupled cloud object storage.

### Key Architectural Highlights:
- **Zero Media in Database**: High-throughput object storage (AWS S3, Cloudflare R2, Cloudinary) via `django-storages` with strict MIME and size whitelists.
- **Full-Duplex WebSockets**: Stateful bi-directional messaging with connection lifecycle hooks, automated reconnect sync, and Redis-backed group broadcasts.
- **Production-Grade Security**: Split environment settings (`base`/`dev`/`prod`), strict `ALLOWED_HOSTS`, fail-fast secret checks, and Fernet encryption at rest for direct messages.
- **Automated Verification**: Comprehensive test suite featuring **68 tests** (pytest + pytest-django + pytest-asyncio) backed by multi-version Python matrix CI on GitHub Actions.

---

## 🏗️ System Architecture

Zyra uses an asynchronous server gateway interface (ASGI) architecture powered by **Daphne** and **Django Channels**, decoupling synchronous HTTP request cycles from long-lived WebSocket chat connections:

```mermaid
flowchart TD
    Client["Browser / Mobile Client"]

    subgraph Gateway["Edge & ASGI Gateway"]
        ProtocolRouter["config/asgi.py (ProtocolTypeRouter)"]
        DaphneServer["Daphne / Uvicorn ASGI Server"]
    end

    subgraph AppServer["Django Application Server"]
        HTTPHandler["Django WSGI/HTTP Handler (Views & Middleware)"]
        ChatConsumer["ChatConsumer (AsyncJsonWebsocketConsumer)"]
        Services["Business Services (Messaging, Feeds, Auth)"]
    end

    subgraph StateAndCache["State & Distributed Cache"]
        RedisServer[("Redis 7 (channels_redis)")]
    end

    subgraph DataStorage["Data Persistence & Media"]
        PostgresDB[("PostgreSQL Database")]
        ObjectStorage[("Cloud Object Storage (S3 / R2 / Cloudinary)")]
    end

    Client -->|HTTP / HTTPS| DaphneServer
    Client -->|WSS (WebSockets)| DaphneServer
    DaphneServer --> ProtocolRouter
    ProtocolRouter -->|http| HTTPHandler
    ProtocolRouter -->|websocket| ChatConsumer

    HTTPHandler --> Services
    ChatConsumer <-->|Pub/Sub Groups & Presence| RedisServer
    ChatConsumer -->|Database Sync-to-Async| PostgresDB
    Services --> PostgresDB
    Services -->|Upload & Presigned Keys| ObjectStorage
    Client -->|Stream Videos / View Media| ObjectStorage
```

---

## 🚀 Core Features

### 1. 📱 Dynamic Home Feed & Interactions
- **Rich Media**: Upload photos and portrait videos with captions up to 1,000 characters.
- **Optimized Double-Tap**: Double-click or tap media to trigger an animated heart burst with immediate AJAX reaction.
- **Live Comments & Bookmarks**: Add threaded comments and toggle private bookmarks without full page reloads.
- **Cursor Pagination & Infinite Scroll**: Server-side batching with asynchronous DOM hydration.

### 2. ⏳ Ephemeral 24-Hour Stories
- Photo/video stories with optional background music soundtracks.
- Automatic 24-hour expiration queries (`created_at >= timezone.now() - timedelta(hours=24)`).
- Fullscreen stories carousel featuring animated progress bars, touch/mouse hold-to-pause gestures, and author deletion rights.

### 3. 🎬 Vertical Video Reels
- Snap-scrolling video feed with auto-looping playback.
- Viewport intersection observer triggering 60fps playback when visible and pausing when scrolled off-screen.
- Global audio mute/unmute state shared across active reel items.

### 4. 💬 Real-Time Direct Messaging (Instagram Direct)
- **Full-Duplex WebSockets**: Real-time message push with latency < 50ms.
- **Connection Recovery & Sync**: Clients reconnect with `last_message_id` to automatically backfill messages missed during network dropouts.
- **Voice Notes**: In-browser audio recording using the native `MediaRecorder` API with animated waveform visualizers.
- **Chat Enhancements**: Message editing within a 5-minute window, global unsend/delete, emoji reactions tray, and real-time typing indicators.
- **Fernet Encryption**: Direct message contents are encrypted at rest with symmetric encryption before hitting PostgreSQL.

### 5. 👤 Social Graph & Profile Management
- Customizable user bio, avatar, pronouns, and last-seen activity timestamps.
- Follow/unfollow mechanics with real-time follower/following count counters.
- Dynamic profile search and creator recommendations.

---

## 🛠️ Tech Stack

| Domain | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Django 5.2 | High-level Python web framework with secure ORM and auth |
| **ASGI Engine** | Django Channels 4.2 + Daphne | Asynchronous protocol router handling WebSockets and HTTP |
| **Channel Layer** | Redis 7 + `channels_redis` | High-throughput distributed pub/sub and state synchronization |
| **Database** | PostgreSQL / SQLite | Relational persistence with foreign-key cascades and indexing |
| **Object Storage** | `django-storages` + `boto3` | Zero media in DB; direct streaming from Cloudflare R2 / S3 / Cloudinary |
| **Frontend** | Vanilla ES6 Modules + CSS3 | Modular browser-native scripts (`static/js/modules/`) & dark glassmorphism |
| **Testing** | `pytest`, `pytest-django`, `pytest-asyncio` | Unit, integration, and async WebSocket tests (68 tests) |
| **CI/CD** | GitHub Actions | Automated build and test matrix (Python 3.11, 3.12, 3.13 + Redis service) |
| **Containers** | Docker & Docker Compose | Containerized multi-service development and deployment |

---

## 📂 Repository Structure

```text
Zyra/
├── .github/workflows/ci.yml # GitHub Actions multi-version CI pipeline
├── config/                  # Core Django configuration
│   ├── settings/            # Modularized environment settings
│   │   ├── __init__.py      # Auto-loads dev vs prod based on DJANGO_ENV
│   │   ├── base.py          # Shared apps, middleware, password validators
│   │   ├── dev.py           # Local dev settings (DEBUG=True, SQLite, InMemory)
│   │   └── prod.py          # Production settings (SSL, Redis check, Secret Key)
│   ├── asgi.py              # ProtocolTypeRouter (HTTP + Channels WebSocket)
│   ├── urls.py              # Root URL router
│   └── wsgi.py              # Fallback WSGI interface
├── core/                    # Main application package
│   ├── consumers.py         # AsyncJsonWebsocketConsumer (ChatConsumer)
│   ├── models.py            # Relational models (Post, Story, Conversation, Message)
│   ├── routing.py           # WebSocket URL patterns (/ws/chat/<id>/)
│   ├── serializers.py       # DTO dictionary serializers
│   ├── storage.py           # Custom Cloudinary and S3 storage adapters
│   ├── forms.py             # Form validations (PostForm, CommentForm, Auth)
│   ├── utils/
│   │   ├── media.py         # Strict MIME/size whitelist and Pillow compression
│   │   └── rate_limit.py    # Decorator-based Redis/Cache rate limiting
│   └── views/               # Domain controllers (feed, direct, reels, stories, auth)
├── static/                  # Client-side static assets
│   ├── css/style.css        # Dark glassmorphic design system
│   ├── img/                 # SVG logos, avatars, and favicons
│   └── js/                  # Modular ES6 JavaScript architecture
│       ├── utils/api.js     # CSRF & fetch helpers
│       └── modules/         # Extracted modules (base.js, home.js, reels.js, direct.js)
├── templates/core/          # Server-rendered HTML templates
│   ├── base.html            # Navigation sidebar, toast manager, modals
│   ├── home.html            # Feed stream and stories tray
│   ├── reels.html           # Vertical snap-scrolling video feed
│   └── direct.html          # Dual-column real-time messaging interface
├── tests/                   # Pytest test suite (68 tests)
│   ├── conftest.py          # Shared fixtures (users, clients, media bytes)
│   ├── test_auth.py         # Registration, login, logout, password reset
│   ├── test_posts_feed.py   # Feed ordering, creation, permissions, pagination
│   ├── test_interactions.py # Likes, comments, bookmarks, follows
│   ├── test_stories.py      # 24h expiry queries, story creation, author delete
│   ├── test_reels.py        # Video uploads, MIME validation, reels feed
│   └── test_websockets.py   # Channels WebsocketCommunicator async suite
├── docker-compose.yml       # Web (Daphne), Redis, and Postgres services
├── Dockerfile               # Multi-stage production container build
├── Procfile                 # Process launcher for PaaS (web: daphne)
├── fly.toml                 # Fly.io deployment blueprint
├── render.yaml              # Render blueprint specification
├── railway.toml             # Railway deployment configuration
├── pytest.ini               # Pytest configuration
└── requirements.txt         # Pinned production and testing dependencies
```

---

## 💻 Quickstart: Local Development

### 1. Prerequisites
- **Python**: 3.11, 3.12, or 3.13 installed
- **Git**
- Optional: Local Redis instance (required only if running production settings locally)

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone https://github.com/Spidey173/Zyra.git
cd Zyra

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Local Environment Variables
Copy the example environment template:
```bash
cp .env.example .env
```

For development, sensible defaults are automatically selected:
- SQLite database is used if `DATABASE_URL` is omitted.
- `InMemoryChannelLayer` is used for WebSockets when `DEBUG=True`.
- Local filesystem storage is used if S3/Cloudinary variables are omitted.

### 4. Run Migrations and Start the Development Server
```bash
# Apply database migrations
python manage.py migrate

# (Optional) Create a superuser account
python manage.py createsuperuser

# Start the ASGI development server
python manage.py runserver
```

Open **`http://127.0.0.1:8000`** in your browser.

---

## 🐳 Docker Setup

Zyra includes a production-ready `Dockerfile` and `docker-compose.yml` orchestrating the ASGI web application, PostgreSQL 16 database, and Redis 7 service.

### Launch Multi-Container Stack:
```bash
docker-compose up --build
```

The stack initializes:
- **`web`**: Daphne running `config.asgi:application` on port `8000`.
- **`postgres`**: PostgreSQL 16 on port `5432` with persistent volume `postgres_data`.
- **`redis`**: Redis 7 Alpine on port `6379` with healthcheck inspection.

---

## 🧪 Running the Test Suite

Zyra uses `pytest` and `pytest-django` to run its test suite:

```bash
# Run the complete test suite
pytest -v

# Run a specific domain module
pytest tests/test_websockets.py -v

# Run with coverage report
pytest --cov=core
```

You can also run Django's native test runner:
```bash
python manage.py test
```

---

## ⚙️ Environment Variables

Zyra strictly manages settings via environment variables. In production, missing critical keys causes an immediate startup crash.

| Variable | Description | Default | Required in Prod |
| :--- | :--- | :--- | :--- |
| `DJANGO_ENV` | Environment mode (`dev` or `prod`) | `dev` | **Yes** (`prod`) |
| `DEBUG` | Enable/disable debug diagnostics | `False` | **Yes** (`False`) |
| `SECRET_KEY` | Cryptographic secret key for signing sessions & tokens | Auto-generated in dev | **Yes** (>= 32 chars) |
| `ALLOWED_HOSTS` | Comma-separated list of valid domain names (no `*`) | `localhost,127.0.0.1` | **Yes** |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins (`https://...`) | Unset | **Yes** |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql://user:pass@host:5432/db`) | SQLite database | Recommended |
| `REDIS_URL` | Redis connection URL for Channels (`redis://...`) | In-Memory (Dev only) | **Yes** |
| `DEFAULT_STORAGE_BACKEND` | Storage provider (`django-storages` S3, R2, Cloudinary, or local) | FileSystemStorage | Recommended |
| `AWS_STORAGE_BUCKET_NAME`| S3 or Cloudflare R2 bucket name | Unset | If using S3/R2 |
| `AWS_ACCESS_KEY_ID` | Storage access key ID | Unset | If using S3/R2 |
| `AWS_SECRET_ACCESS_KEY` | Storage secret access key | Unset | If using S3/R2 |
| `AWS_S3_ENDPOINT_URL` | Endpoint URL (e.g. `https://<id>.r2.cloudflarestorage.com`) | AWS S3 Default | If using R2/MinIO |
| `CLOUDINARY_URL` | Cloudinary credentials (`cloudinary://key:secret@cloud`) | Unset | If using Cloudinary |
| `FERNET_KEY` | 32-byte base64 key for DM encryption at rest | Auto-derived from secret | Optional |

---

## 🚢 Deployment Guides

### Deploy to Render
Zyra contains a preconfigured [render.yaml](file:///Users/spidey./Downloads/Spidey/Zyra/render.yaml) blueprint:
1. Connect your repository on [Render](https://render.com/).
2. Select **New > Blueprint** and link the repo.
3. Render automatically provisions the Daphne web service, Redis instance, and PostgreSQL database.
4. Set `SECRET_KEY` and your object storage variables in the Render dashboard.

### Deploy to Railway
Zyra contains a [railway.toml](file:///Users/spidey./Downloads/Spidey/Zyra/railway.toml) deployment specification:
1. Run `railway init` or link the repository from the Railway Dashboard.
2. Add a **PostgreSQL** plugin and a **Redis** plugin from the Railway canvas.
3. Railway automatically binds `DATABASE_URL` and `REDIS_URL`.
4. The service boots via `Procfile` using Daphne.

### Deploy to Fly.io
Zyra includes a pre-configured [fly.toml](file:///Users/spidey./Downloads/Spidey/Zyra/fly.toml):
```bash
fly launch
fly redis create
fly postgres create
fly deploy
```

---

## 📸 Screenshots

<div align="center">

### Home Feed & Stories Tray
*(Screenshot Placeholder — Insert `/docs/screenshots/feed.png`)*
*Explore stories carousel, double-tap hearts, dynamic comment stream, and following filter.*

### Full-Duplex Direct Messaging
*(Screenshot Placeholder — Insert `/docs/screenshots/chat.png`)*
*Real-time WebSockets communication, voice notes recording, audio waveforms, and reaction trays.*

### Snap-Scroll Video Reels
*(Screenshot Placeholder — Insert `/docs/screenshots/reels.png`)*
*Vertical video reels with 60fps intersection observer autoplay and unified audio toggling.*

</div>

---

## 💡 Key Design Decisions

### 1. Why Kill Media-in-Postgres for Object Storage?
- **Database Bloat & Thrashing**: Storing raw images, audio clips, and 50MB video files as binary data (`BinaryField` or byte streams) inside PostgreSQL causes exponential table growth, destroys write-ahead log (WAL) efficiency, degrades cache hits, and complicates backups.
- **Resource Starvation**: Serving large video files through Django application threads blocks database connections and starves CPU resources.
- **The Solution**: Migrating to cloud object storage (Cloudflare R2 or Amazon S3 via `django-storages`) offloads 100% of binary payload handling. The database stores only lightweight URI references. Media is served directly over global CDNs with HTTP range requests and edge caching.

### 2. Why ASGI & Channels over WSGI Polling?
- **Sub-50ms Latency**: Traditional polling loops (`GET /messages/?since=...`) waste bandwidth, cause database query spikes, and delay incoming messages by several seconds.
- **True Push Architecture**: ASGI with Daphne and Django Channels establishes persistent, lightweight WebSockets. New messages, typing indicators, and emoji reactions are broadcast to room participants via Redis pub/sub within milliseconds.
- **Connection Recovery**: The consumer implements protocol-level reconnection (`{"action": "sync", "last_message_id": 123}`) to deliver messages sent while the client was temporarily offline.

### 3. Why Modular ES6 JavaScript over 150KB Inline Template Scripts?
- **Zero Script Spaghetti**: Monolithic inline `<script>` tags across templates lead to code duplication, browser caching issues, and difficult testing.
- **Security & Hygiene**: Injecting dynamic Django context (`{{ ... }}`) directly into JavaScript code creates potential Cross-Site Scripting (XSS) vectors.
- **The Solution**: All frontend scripts are organized into browser-native ES6 modules (`static/js/modules/`). Server context is passed safely via HTML5 `data-*` attributes and `<script type="application/json">` elements, keeping the presentation layer testable and clean.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
