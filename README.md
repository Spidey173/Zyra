# ✨ Zyra — Next-Gen Social Media & Real-Time Chat

A modern, fast, and beginner-friendly social media web app inspired by Instagram. Built using **Python & Django 5**, **WebSockets (Django Channels)**, and **Neon PostgreSQL**.

---

## 🌟 What Can You Do on Zyra?

### 💬 1. Instant Direct Messaging (Instagram Style)
- **⚡ Super Fast Chat**: Real-time messaging with live typing indicators.
- **✏️ Edit Messages**: Edit any message within 5 minutes.
- **🗑️ Delete / Unsend**: Unsend any message anytime.
- **❤️ Emoji Reactions**: Quick-react to messages with hearts and emojis.
- **🟢 Live Online Status**: Shows *"Active now"* or *"Active 5m ago"* accurately.

### 📸 2. Feed, Reels & Stories
- **📱 Home Feed**: Share photos, captions, and like with a double-tap ❤️.
- **🎥 60fps Reels**: Vertical video scroll experience.
- **⏳ 24h Stories**: Share photos/videos with music and an easy **Delete Story** button.
- **💬 Comments & Likes**: Comment, like, and bookmark posts instantly.

### 👤 3. Profiles & Social Graph
- **Personalized Profile**: Add bio, pronouns, and custom avatar.
- **Follow / Unfollow**: Follow creators and view follower lists.

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

## 🔑 Demo Login Accounts

You can register a new account on the signup page or log in with the test accounts:

| Username | Password | Role |
| :--- | :--- | :--- |
| **`Spidey`** | **`Spidey@173`** | Superuser / Admin |
| **`Ash`** | **`Password123!`** | Tester / Chat Partner |

---

## 📂 Project Structure

```text
Zyra/
├── config/              # Django settings, URLs, and ASGI/WSGI setup
├── core/                # Main application logic
│   ├── consumers.py     # WebSocket logic for real-time messaging
│   ├── models.py        # Database models (User, Post, Message, Story, etc.)
│   ├── views/           # Views (Feed, Reels, Stories, Direct Chat, Profile)
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

Zyra is 100% ready for free deployment on **Render**:

1. Push your code to **GitHub**.
2. Create a new **Web Service** on [Render Dashboard](https://dashboard.render.com/).
3. Connect your repository and configure:
   - **Build Command**: `./build.sh`
   - **Start Command**: `daphne -b 0.0.0.0 -p $PORT config.asgi:application`
4. Add your **Environment Variables**:
   - `DATABASE_URL`: `postgresql://<user>:<password>@<neon-host>/neondb?sslmode=require`
   - `PYTHON_VERSION`: `3.11.9`
   - `DEBUG`: `False`
   - `SECRET_KEY`: `<your-random-secret-key>`
5. Click **Deploy Web Service**!

---

## 💡 Tech Stack
- **Backend**: Python 3.11+, Django 5.2
- **Real-Time WebSockets**: Django Channels, Daphne ASGI
- **Database**: SQLite (Local) / Neon PostgreSQL (Production)
- **Frontend**: HTML5, Vanilla CSS3 (Dark Glassmorphism), Bootstrap Icons

---

Made with ❤️ by the Zyra Team.
