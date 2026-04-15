# Zyra - Social Media Platform

![Django](https://img.shields.io/badge/Django-5.2.4-green)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

A modern, full-featured Django-based social media platform that enables users to connect, share posts, and interact with their community in real-time.

## 📚 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Data Model](#-data-model)
- [API Routes](#-api-routes)
- [Development Guide](#-development-guide)
- [Troubleshooting](#-troubleshooting)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### Authentication & User Management
- ✅ User registration with secure password validation
- ✅ Login/logout with Django session management
- ✅ Customizable user profiles with bio and profile pictures
- ✅ Profile metadata (followers/following counts)

### Social Interactions
- 📸 **Posts**: Share images and captions with your community
- 👍 **Likes**: Like and unlike posts from other users
- 💬 **Comments**: Leave comments on posts for engagement
- 👥 **Follow System**: Follow/unfollow users to stay connected
- 🔗 **Social Graph**: View followers and following lists

### Performance & UX
- ⚡ Optimized database queries using `select_related()` and `prefetch_related()`
- 📱 Responsive Bootstrap 5 design
- 🔒 Django's built-in security features
- 📊 Django admin panel for content management

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 5.2.4 |
| **Language** | Python 3.13 |
| **Database** | SQLite (development) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **UI Framework** | Bootstrap 5 (CDN) |
| **Authentication** | Django built-in |
| **Media** | Pillow (image processing) |

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or Poetry
- Virtual environment manager

### 1️⃣ Clone the Repository

```bash
git clone <repository-url>
cd Zyra
```

### 2️⃣ Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install "Django==5.2.4" Pillow
```

### 4️⃣ Apply Migrations

```bash
python manage.py migrate
```

### 5️⃣ Create Superuser

```bash
python manage.py createsuperuser
```

### 6️⃣ Run Development Server

```bash
python manage.py runserver
```

### 7️⃣ Access Application

- **Main App**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/

## 📁 Project Structure

```text
Zyra/
├── config/                      # Django project configuration
│   ├── settings.py             # Project settings & installed apps
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI application
│   └── asgi.py                 # ASGI application
│
├── core/                        # Main social media application
│   ├── models.py               # Database models
│   ├── views.py                # View logic & handlers
│   ├── forms.py                # Django forms
│   ├── urls.py                 # App URL routing
│   ├── admin.py                # Admin configuration
│   └── migrations/             # Database migrations
│
├── templates/core/             # HTML templates
│   ├── base.html               # Base template
│   ├── home.html               # Feed page
│   ├── landing.html            # Landing page
│   ├── login.html              # Login form
│   ├── register.html           # Registration form
│   ├── user_profile.html       # User profile
│   ├── post_detail.html        # Post with comments
│   ├── followers_list.html     # Followers view
│   └── following_list.html     # Following view
│
├── media/                      # User uploaded files
│   └── posts/                  # Post images
├── static/                     # Static assets
├── db.sqlite3                  # SQLite database
├── manage.py                   # Django CLI
└── README.md                   # This file
```

## 📊 Data Model

The `core` app defines the following models:

### UserProfile
Extends Django's built-in User model with social profile information.
```
├── user (OneToOneField) → Django User
├── bio (TextField) → User biography
└── profile_pic (ImageField) → Profile picture
```

### Post
User-generated content with multimedia support.
```
├── user (ForeignKey) → Author
├── caption (TextField) → Post description
├── image (ImageField) → Optional image
└── created_at (DateTimeField) → Timestamp
```

### Like
Tracks user engagement with posts (unique per user-post pair).
```
├── user (ForeignKey) → User
├── post (ForeignKey) → Post
└── Constraint: unique_together(user, post)
```

### Comment
Enables threaded discussions on posts.
```
├── user (ForeignKey) → Author
├── post (ForeignKey) → Target post
├── content (TextField) → Comment text
└── created_at (DateTimeField) → Timestamp
```

### Follow
Manages the social graph between users.
```
├── follower (ForeignKey) → User initiating follow
├── following (ForeignKey) → User being followed
└── Constraint: unique_together(follower, following)
```

## 🔌 API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Landing page (redirects to home if authenticated) |
| `/register/` | GET, POST | User registration |
| `/login/` | GET, POST | User login |
| `/logout/` | GET | User logout |
| `/home/` | GET, POST | Authenticated feed (create posts here) |
| `/post/<post_id>/` | GET, POST | Post detail with comments |
| `/post/like/<post_id>/` | POST | Toggle like on post |
| `/post/comment/<post_id>/` | POST | Add comment to post |
| `/user/<username>/` | GET | View user's profile & posts |
| `/user/<username>/follow/` | POST | Toggle follow/unfollow |
| `/profile/<username>/followers/` | GET | View user's followers |
| `/profile/<username>/following/` | GET | View user's following list |
| `/admin/` | GET | Django admin panel |

## 💻 Development Guide

### Common Django Commands

**Check project health:**
```bash
python manage.py check
```

**Create new migrations after model changes:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**Run tests:**
```bash
python manage.py test
```

**Access Django shell:**
```bash
python manage.py shell
```

**Create sample data:**
```python
from django.contrib.auth.models import User
from core.models import Post, UserProfile

user = User.objects.create_user(username='testuser', password='testpass')
UserProfile.objects.create(user=user, bio='Test user')
```

### Static Files

Collect static files for production:
```bash
python manage.py collectstatic
```

During development with `DEBUG = True`, Django serves static files automatically.

### Media Files

Uploaded images are stored in `media/` during development:
- Post images → `media/posts/`
- Profile pictures → `media/profile_pics/`

For production, configure cloud storage (S3, Cloudinary, etc.)

## 🔧 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'PIL'`
**Solution**: Install Pillow for image handling
```bash
pip install Pillow
```

### Issue: `TemplateDoesNotExist`
**Solution**: Ensure `TEMPLATES` is configured in `settings.py` and template directories exist

### Issue: Media files not uploading
**Solution**: Verify `MEDIA_URL` and `MEDIA_ROOT` in settings, and ensure `DEBUG = True` for development

### Issue: "No such table" error
**Solution**: Run migrations
```bash
python manage.py migrate
```

### Issue: Social features not working (like, follow, etc.)
**Solution**: Ensure you're logged in. Protected views require authentication via `@login_required` decorator

## 📦 Creating Requirements File

To freeze current dependencies:
```bash
pip freeze > requirements.txt
```

Or create manually:
```bash
cat > requirements.txt << EOF
Django==5.2.4
Pillow>=10.0.0
EOF
```

For future installs:
```bash
pip install -r requirements.txt
```

## 🚢 Deployment

### Pre-deployment Checklist

- [ ] Create `.gitignore` for `venv/`, `db.sqlite3`, `media/`, `__pycache__/`
- [ ] Set `DEBUG = False`
- [ ] Use environment variables for `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up static/media storage (S3, Cloudinary, etc.)
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Enable HTTPS
- [ ] Run security checks: `python manage.py check --deploy`

### Environment Variables

Create `.env` file:
```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgres://user:password@localhost/dbname
```

### Settings for Production

```python
# settings.py
import os
from pathlib import Path

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

## 🎯 Suggested Improvements

### Quick Wins
- [ ] Add `requirements.txt` for easier dependency management
- [ ] Add `.gitignore` for version control
- [ ] Add automated tests for authentication, posting, likes, comments
- [ ] Add profile editing UI
- [ ] Move inline CSS to static stylesheets

### Medium Priority
- [ ] Implement pagination for feed and profile posts
- [ ] Add AJAX for likes and comments (no page refresh)
- [ ] Add user search functionality
- [ ] Add hashtag support for posts
- [ ] Add post delete/edit functionality
- [ ] Add email verification for registration

### Advanced Features
- [ ] Real-time notifications using WebSockets
- [ ] Direct messaging between users
- [ ] Story/ephemeral content feature
- [ ] Post sharing/repost feature
- [ ] Trending posts algorithm
- [ ] User recommendations

## 📝 License

This project is open source and available under the **MIT License**.

Add a `LICENSE` file before publishing:
```bash
curl https://opensource.org/licenses/MIT -o LICENSE
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
   ```bash
   git clone <your-fork-url>
   cd Zyra
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Write clean, documented code
   - Follow PEP 8 style guide
   - Test your changes

4. **Commit with meaningful messages**
   ```bash
   git commit -m 'Add amazing feature: description'
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**
   - Describe changes clearly
   - Link relevant issues
   - Request review

### Code Style Guidelines
- Use 4 spaces for indentation
- Write descriptive variable names
- Add docstrings to complex functions
- Keep lines under 100 characters

## 📞 Support & Questions

- **Report Issues**: Open an issue on GitHub
- **Security**: Report security issues privately to maintainers
- **Questions**: Start a discussion or contact the team

---

**Last Updated**: April 2026
