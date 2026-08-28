# 🌌 Zyra - Next-Gen Social Media & Real-Time Messaging Platform

<div align="center">

![Zyra Hero](static/css/style.css)

**Zyra** is a state-of-the-art, full-featured social platform built with **Django 5**, **Django Channels (ASGI)**, **Daphne**, and **Neon PostgreSQL**. Designed with an edge-to-edge Instagram aesthetic, dark mode styling, and sub-30ms real-time messaging.

[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Django%20Channels-0c4b33?style=for-the-badge&logo=django&logoColor=white)](https://channels.readthedocs.io/)
[![Database](https://img.shields.io/badge/Neon-PostgreSQL-00e699?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![Server](https://img.shields.io/badge/ASGI-Daphne-4B8BBE?style=for-the-badge&logo=python&logoColor=white)](https://github.com/django/daphne)
[![Deployment](https://img.shields.io/badge/Render-Ready-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

</div>

---

## ✨ Key Features

### ⚡ Real-Time Direct Messaging (Instagram Direct Experience)
- **⚡ Sub-30ms Instant Delivery**: Full-duplex WebSockets powered by **Django Channels** and **Daphne ASGI**.
- **✏️ 5-Minute Message Editing**: Edit your sent messages strictly within 5 minutes of creation, tagged with live `(edited)` indicators.
- **🗑️ Delete / Unsend Anytime**: Seamlessly delete your messages for all participants with zero time restrictions.
- **😍 Interactive Emoji Reactions**: React to any message with persistent emoji badges (`❤️`, `🔥`, `😂`, `😮`, `😢`, `👏`, `👍`) synced in real time.
- **💬 Live Typing Indicators**: Real-time 3-dot animated pulse when your chat partner is typing.
- **🛡️ Hybrid Fallback Sync**: Resilient background polling takes over automatically if a connection drops.
- **🖼️ Rich Media & Post Sharing**: Share photos and preview shared feed posts directly in direct message bubbles.

### 📸 Feed, Reels & Stories
- **Interactive Home Feed**: Infinite scrolling, double-tap heart liking, bookmarking, and post detail modal.
- **Reels Experience**: Dedicated immersive video player with vertical media feeds.
- **Stories with Music & Expiry**: Share 24-hour visual stories with custom audio tracks.
- **Comment Management**: Comment on posts and delete comments in real time with AJAX.

### 🔔 Activity & Notifications
- **Filtered Activity**: Filter notifications strictly by **Comments** and **Follows** with dynamic empty-state handling and unread badge sync.

### 👤 Profile & Social Graph
- **Personalized Profiles**: Bio, gender pronouns, avatars, followers / following modal views, and instant AJAX follow/unfollow toggle.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | [Django 5.2](https://www.djangoproject.com/) (Python 3.11+) |
| **Real-Time Asynchronous Engine** | [Django Channels](https://channels.readthedocs.io/) & [Daphne ASGI](https://github.com/django/daphne) |
| **Production Database** | [Neon Serverless PostgreSQL](https://neon.tech/) (with Connection Pooling & SSL) |
| **Channel Layer** | In-Memory (Standard) / [Redis](https://redis.io/) (High-Scale Multi-Instance) |
| **Static Assets** | [WhiteNoise](http://whitenoise.evans.io/) Compressed Storage |
| **Styling & UI** | Custom Vanilla CSS3, Glassmorphism, Bootstrap 5 Icons |

---

## 🚀 One-Click Deploy to Render

Zyra is fully pre-configured for instant deployment on [Render](https://render.com/) via `render.yaml`, `build.sh`, and `Procfile`.

### Steps to Deploy:
1. Fork or push this repository to your **GitHub** account.
2. Log in to **[Render Dashboard](https://dashboard.render.com/)**.
3. Click **New +** $\rightarrow$ **Web Service** $\rightarrow$ connect your **Zyra** repository.
4. Set the following parameters:
   - **Environment**: `Python`
   - **Build Command**: `./build.sh`
   - **Start Command**: `daphne -b 0.0.0.0 -p $PORT config.asgi:application`
5. Configure your **Environment Variables**:
   - `DATABASE_URL`: `postgresql://neondb_owner:...@...neon.tech/neondb?sslmode=require`
   - `SECRET_KEY`: *(Generate secure key)*
   - `PYTHON_VERSION`: `3.11.9`
   - `DEBUG`: `False`
6. Click **Create Web Service**!

---

## 💻 Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Spidey173/Zyra.git
cd Zyra
```

### 2. Create and Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Database & Environment
Create a `.env` file or export your connection string:
```bash
export DATABASE_URL="postgresql://neondb_owner:npg_hqrO7D5glaKj@ep-round-smoke-ael2llxu-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
```

### 5. Run Database Migrations
```bash
python manage.py migrate
```

### 6. Start the Daphne ASGI Server
```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```
Visit **`http://127.0.0.1:8000/`** to explore Zyra!

---

## 🔒 Security & Performance Features
- **AllowedHostsOriginValidator**: Secures WebSocket handshake origins against cross-site hijacking.
- **5-Minute Message Lock**: Prevents unauthorized message tampering beyond the 5-minute window.
- **Prepared Database Indices**: Optimized index on `(conversation, created_at)` and `(sender, created_at)` for instant DB lookups.
- **CSRF Token Protection**: Global cookie extraction with secure HTTPS origin verification.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
