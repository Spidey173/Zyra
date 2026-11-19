# Zyra — Full-Stack Social Media Platform

A full-stack social media web application inspired by Instagram, built with **Python**, **Django**, **PostgreSQL**, and **JavaScript**. Features include interactive media feeds, 24-hour stories, user profiles, and direct messaging with encryption at rest and optimistic UI updates.

<div align="center">

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Demo-zyra17.vercel.app-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://zyra17.vercel.app/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/Neon-PostgreSQL-00e699?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![Cloudinary](https://img.shields.io/badge/CDN-Cloudinary-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white)](https://cloudinary.com/)

**[👉 Launch Live Application: https://zyra17.vercel.app/](https://zyra17.vercel.app/)**

</div>

---

## 📌 Project Overview

**Zyra** is a full-stack social media application designed with an emphasis on scalable architecture, clean relational modeling, and responsive user experience. 

Key engineering highlights:
- **Clean Relational Schema**: Designed schemas for user profiles, posts, comments, likes, follower graphs, conversations, and messages with foreign keys and cascade rules.
- **Backend Architecture**: Built modular Django apps adhering to the Model-View-Template (MVT) architecture with reusable service layers and custom querysets.
- **Query & CDN Optimization**: Eliminated N+1 queries using `select_related` and `prefetch_related`, while routing media through Cloudinary with automatic WebP/AVIF format and quality compression (`f_auto, q_auto`).
- **Interactive UI**: Responsive dark glassmorphism interface built with semantic HTML5, Vanilla CSS3, and JavaScript (Fetch API, DOM manipulation, optimistic UI).
- **Serverless Cloud Deployment**: Hosted on Vercel connected to a serverless Neon PostgreSQL database.

---

## 🔑 Demo Test Accounts

You can register a new account on the signup page or test with pre-configured accounts:

| Username | Password | Role |
| :--- | :--- | :--- |
| **`Spidey`** | **`Spidey@173`** | Creator / Admin |
| **`Ash`** | **`Password123!`** | Chat Partner / Tester |

---

## 🚀 Features

### 1. 📱 Home Feed & Interactions
- **Photos & Videos**: Upload photos or portrait video clips with captions.
- **Double-Tap Like**: Like posts with an animated heart overlay or toggle using the heart icon.
- **Quick Comments & Bookmarks**: Post inline comments and save posts with instant AJAX feedback.
- **Aspect Ratio Handling**: Centered layout capping tall 9:16 portrait media to `560px` so like/comment action bars remain immediately accessible.

### 2. 💬 Direct Messages
- **Encrypted at Rest**: Message text is secured using **Fernet symmetric encryption** derived from the application key.
- **Fast First Paint**: Chat history is pre-rendered server-side (SSR) into the DOM, eliminating white-screen delays.
- **Interactive Chat Tools**:
  - **Edit within 5 mins**: Senders can edit recent messages within a 5-minute window.
  - **Unsend / Delete**: Remove messages for both participants.
  - **Emoji Reactions**: Double-tap a bubble to heart it or choose from floating emoji trays.
  - **Voice Notes**: In-browser microphone recording with waveform visualizer and audio playback.
- **Serverless Resilience**: Optimistic client-side rendering with incremental polling fallback (`?since_id=...`) ensuring seamless real-time message sync on serverless infrastructure.

### 3. ⏳ Ephemeral 24-Hour Stories
- Upload photo/video stories that automatically expire after 24 hours (`created_at >= now - 24h`).
- Homepage story tray features a gradient ring and an author delete option.

### 4. 👤 User Profiles & Social Graph
- Editable profile bio, pronouns, and avatar with universal fallback placeholders.
- Follow and unfollow creators with dynamic follower / following count updates.
- Suggested creators recommendations based on follow status.

---

## 🛠️ Tech Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Backend** | Python 3.11, Django 5.2 | Django MVT, ORM, Session Authentication, CSRF protection |
| **Database** | PostgreSQL (Neon) / SQLite | ACID compliance, connection pooling, SSL; SQLite for local offline use |
| **Media CDN** | Cloudinary | Automatic format (`f_auto`) and quality compression (`q_auto`) |
| **Frontend** | HTML5, Vanilla CSS3, JavaScript | Modern CSS Custom Properties (Dark Glassmorphism), Fetch API, DOM updates |
| **Hosting** | Vercel Serverless | Edge routing, automated CI/CD pipeline |

---

## 📂 Project Structure

```text
Zyra/
├── config/                  # Django project configuration
│   ├── settings.py          # Environment settings (database, storage, security)
│   ├── urls.py              # Root URL routing
│   ├── asgi.py              # ASGI interface
│   └── wsgi.py              # WSGI interface
├── core/                    # Core social media application
│   ├── models.py            # Schemas (User, Profile, Post, Comment, Message, Story)
│   ├── views/               # View controllers (feed, direct, profile, stories, auth)
│   ├── services/            # Reusable business logic (messaging, feed queries)
│   ├── utils/               # Encryption, media validation, rate limiting
│   ├── storage.py           # Custom Cloudinary media storage backend
│   └── serializers.py       # DTO serialization for JSON endpoints
├── templates/core/          # Django HTML templates
│   ├── base.html            # Main layout, sidebar navigation, toast notifications
│   ├── home.html            # Feed stream and stories tray
│   ├── direct.html          # Dual-column messaging interface
│   └── post_list_partial.html # Reusable post card component
├── static/                  # CSS styling, icons, and frontend JavaScript
├── api/                     # Vercel serverless gateway (index.py)
├── vercel.json              # Vercel deployment routes and static rewrites
└── requirements.txt         # Pinned Python package dependencies
```

---

## 💡 Technical Highlights & Architecture Decisions

### 1. Framework Choice & Security Baseline
Django was selected for its robust security defaults and batteries-included architecture. Features like session management, CSRF validation, password hashing (PBKDF2), and SQL-injection-safe ORM queries allowed focusing on core application features without compromising security fundamentals.

### 2. Media Optimization & Bandwidth Reduction
Social applications handle substantial media volume. Serving raw uploads directly from the application container leads to high bandwidth consumption and slow load times. Integrating Cloudinary with automatic format conversion (`fetch_format='auto'`) and perceptual compression (`quality='auto'`) reduced image transfer sizes from ~2.2 MB down to ~240 KB (~89% payload reduction) while preserving visual fidelity.

### 3. Serverless Messaging Architecture
Standard WebSocket implementations rely on persistent stateful processes. On serverless hosting platforms like Vercel where containers are ephemeral, persistent socket connections are impractical. Zyra resolves this by pairing:
1. **Optimistic UI Updates**: Displaying sent messages instantly for zero perceived latency.
2. **REST Endpoints**: Securely processing messages via HTTP POST transactions.
3. **Smart Polling**: Fetching incoming messages via lightweight incremental queries filtered by `?since_id=<last_seen_id>`, minimizing database overhead.

### 4. Database Query Tuning (N+1 Prevention)
In social feeds, querying posts and iterating over related authors, profile pictures, and like statuses can trigger N+1 queries. Zyra optimizes these querypaths:
- `select_related('user', 'user__profile')` for single-valued relationships (SQL JOIN).
- `prefetch_related('comments', 'likes')` for many-to-many collections.
This consolidates database roundtrips into single optimized queries per feed batch.

### 5. Message Privacy at Rest
Direct messages are encrypted before insertion into PostgreSQL using Fernet symmetric encryption from Python's `cryptography` library. Ciphertexts are prefixed with `enc::`. Even in the event of direct database inspection, raw message text cannot be decrypted without the secret key.

---

## 💻 Local Setup & Installation

Get Zyra running locally in under 3 minutes:

### 1. Clone the repository
```bash
git clone https://github.com/Spidey173/Zyra.git
cd Zyra
```

### 2. Set up a virtual environment
```bash
# macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# Windows:
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment configuration (optional for local testing)
Zyra automatically defaults to a local SQLite database and media folder if external variables are omitted. To use PostgreSQL or Cloudinary, configure a `.env` file:
```env
SECRET_KEY="your-local-secret-key"
DEBUG=True
DATABASE_URL="postgresql://user:password@localhost:5432/zyra" # or leave unset for SQLite
CLOUDINARY_URL="cloudinary://<key>:<secret>@<cloud_name>"      # or leave unset for local media
```

### 5. Apply migrations and start development server
```bash
python manage.py migrate
python manage.py runserver
```

Open **`http://127.0.0.1:8000`** in your browser.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
