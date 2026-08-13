# 🕷️ SPIDDY WEB DROP

> **"With great power comes great file sharing."**

[![Django](https://img.shields.io/badge/Django-5.0%2B-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Vercel](https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://spiddy-web.vercel.app)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.0-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

**SpiddyWeb** is a high-speed, temporary, anonymous web application for sharing files securely using a **6-digit secret PIN**. No accounts, no trackable data, no bloat—files automatically self-destruct after 24 hours or immediately after a single download.

🌐 **Live Production App**: [https://spiddy-web.vercel.app](https://spiddy-web.vercel.app)

---

## ✨ Features

- 📦 **2 GB Large File Support**: Upload big media, archives, and documents with JS chunked streaming progress.
- 📦 **Multi-File Selection & Auto-Zipping**: Select or drag multiple files; SpiddyWeb bundles them into a `.zip` drop on the fly.
- ❌ **Selected Files Manager**: Interactive preview list allowing users to view sizes and remove individual files before uploading.
- 🔐 **Secret Passcode Protection**: Optional password protection hashed using Django PBKDF2 algorithm.
- ⏱️ **Auto Self-Destruct & One-Time Mode**: Choose 1hr, 6hr, 24hr, 7-day expiry or immediate deletion after 1 download.
- ⏳ **Live Ticking Countdown Timer**: Real-time `HH:MM:SS` ticking countdown on download pages.
- 📱 **QR Code Sharing**: Instant mobile QR code generator on success page.
- 🔊 **Web-Shooter Audio & Visual FX**: Synthesized Web Audio API sound effects, Spider-Sense Tingle toasts, and interactive Canvas cursor web tails.
- 🛡️ **Brute-Force & Security Protection**: 5-attempt PIN lockout, rate-limiting, and executable file extension blocking.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11, Django 6.0, SQLite / PostgreSQL, Redis.
- **Frontend**: Vanilla HTML5/JS, Tailwind CSS, GSAP 3, Web Audio API, JSZip, QRCode.js.
- **Deployment**: Vercel Serverless Functions, Gunicorn, Docker & Docker Compose.

---

## 🚀 Quick Local Setup

1. **Clone Repository**:
   ```bash
   git clone https://github.com/Satbhai444/Spiddy-Web.git
   cd Spiddy-Web
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Database Migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Start Local Server**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   Open `http://127.0.0.1:8000` in your browser.

---

## 🐳 Docker Setup

Run the full stack (Django + Postgres + Redis) using Docker Compose:

```bash
docker-compose up --build
```

---

## 📚 REST API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/upload/` | `POST` | Upload single or chunked file payloads. |
| `/receive/` | `POST` | Validate 6-digit PIN & optional password. |
| `/file/{pin}/download/` | `GET` | Stream raw file binary attachment. |
| `/docs/` | `GET` | Interactive User & API Documentation page. |

---

## 📄 License & Credits

Designed and built for fast, temporary, encrypted file sharing.  
© 2026 **SPIDDY Web Drop**.
