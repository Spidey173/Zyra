# ✨ Zyra — Next-Gen Social Media & Real-Time Chat

A modern, fast, and beginner-friendly social media web app inspired by Instagram. Built using **Python & Django 5**, **WebSockets (Django Channels)**, and **Neon PostgreSQL**.

<div align="center">

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Demo-zyra--fa4v.onrender.com-FF2E93?style=for-the-badge&logo=render&logoColor=white)](https://zyra-fa4v.onrender.com/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Django%20Channels-0c4b33?style=for-the-badge&logo=django&logoColor=white)](https://channels.readthedocs.io/)
[![Neon Database](https://img.shields.io/badge/Neon-PostgreSQL-00e699?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)

### 🚀 **[👉 Click Here to Launch the Live Demo! 👈](https://zyra-fa4v.onrender.com/)**

</div>

---

## 🔑 Demo Test Accounts

You can register your own account on the signup page or test real-time messaging with the pre-configured accounts:

| Username | Password | Role |
| :--- | :--- | :--- |
| **`Spidey`** | **`Spidey@173`** | Superuser / Admin |
| **`Ash`** | **`Password123!`** | Tester / Chat Partner |

---

## 🌟 What Can You Do on Zyra?

### 💬 1. Instant Direct Messaging (Instagram Style)
- **⚡ Super Fast Chat**: Sub-30ms real-time messaging with live typing indicators.
- **✏️ Edit Messages**: Edit any message within 5 minutes of sending.
- **🗑️ Delete / Unsend**: Unsend messages for everyone anytime.
- **❤️ Emoji Reactions**: Quick-react to messages with hearts and emojis.
- **🟢 Live Online Status**: Shows *"Active now"* or accurate elapsed time (*"Active 5m ago"*).

### 📸 2. Feed, Reels & Stories
- **📱 Home Feed**: Share photos, captions, and like with a double-tap ❤️.
- **🎥 60fps Reels**: Vertical video scroll experience.
- **⏳ 24h Stories**: Share photos/videos with custom music and an active **Delete Story** option.
- **💬 Comments & Likes**: Comment, like, and bookmark posts instantly with AJAX.

### 👤 3. Profiles & Social Graph
- **Personalized Profile**: Add bio, pronouns, and custom avatar.
- **Follow / Unfollow**: Follow creators and browse follower lists.

---

## 🚀 Quick Start (Local Setup)

Follow these 3 easy steps to run Zyra on your computer:

### Step 1: Clone & Navigate to Folder
```bash
git clone https://github.com/Spidey173/Zyra.git
cd Zyra
```

### Step 2: Create & Activate Virtual Environment
```bash
# On macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# On Windows:
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install Packages & Run the Server
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Now open **http://127.0.0.1:8000** in your browser and enjoy Zyra! 🎉

---

## 📂 Project Structure

```text
Zyra/
├── config/              # Django settings, URLs, and ASGI/WSGI setup
├── core/                # Main application logic
│   ├── consumers.py     # WebSocket logic for real-time messaging
│   ├── models.py        # Database models (User, Post, Message, Story, etc.)
│   ├── views/           # Views (Feed, Reels, Stories, Direct Chat, Profile)
│   ├── services/        # Business logic & query optimization services
│   └── urls.py          # App URL routes
├── templates/core/      # Modern dark-mode HTML templates
├── static/              # CSS styling, icons, and JavaScript
├── media/               # Uploaded photos, videos, and stories
├── build.sh             # Deployment build script
├── Procfile             # Render ASGI web server command
└── requirements.txt     # Python project dependencies
```

---

## ☁️ Live Cloud Deployment (Render + Neon)

Zyra is 100% configured for deployment on **Render**:

1. Push your code to **GitHub**.
2. Create a new **Web Service** on [Render Dashboard](https://dashboard.render.com/).
3. Connect your repository and configure:
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn -w 2 -k uvicorn.workers.UvicornWorker --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 --bind 0.0.0.0:$PORT config.asgi:application`
4. Add your **Environment Variables**:
   - `DATABASE_URL`: `postgresql://<user>:<password>@<neon-host>/neondb?sslmode=require`
   - `PYTHON_VERSION`: `3.11.9`
   - `DEBUG`: `False`
   - `SECRET_KEY`: `<your-random-secret-key>`
5. Click **Deploy Web Service**!

---

## 💡 Tech Stack
- **Backend**: Python 3.11+, Django 5.2
- **Real-Time WebSockets**: Django Channels, Uvicorn / Daphne ASGI
- **Database**: SQLite (Local) / Neon PostgreSQL (Production)
- **Frontend**: HTML5, Vanilla CSS3 (Dark Glassmorphism), Bootstrap Icons

---

Made with ❤️ by the Zyra Team.
