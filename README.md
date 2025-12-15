# LoreSmith API

[![Checks](https://github.com/BenjaminKag/loresmith-api/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/BenjaminKag/loresmith-api/actions/workflows/checks.yml)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red)](#-license)


LoreSmith is a **worldbuilding backend API** for writers, game developers, and creative teams.
It helps organize **stories, characters, factions, locations, and items**, while providing an **AI-powered story analysis assistant** that delivers structured feedback and insights.

This repository represents the **Proof of Concept (POC)** version of the LoreSmith backend, focused on **API design, data modeling, AI safety, and backend architecture**.

---

## 📸 Demo & Docs

- **Swagger / OpenAPI UI:** 👉 http://127.0.0.1:8000/api/docs
- **Auth:** Token-based (login via `/user/token/`)

All endpoints are fully documented and testable via Swagger.

---

## 🚀 Quickstart (Docker – Recommended)

```bash
git clone https://github.com/BenjaminKag/loresmith-api.git
cd loresmith-api
cp .env.example .env

docker compose up --build
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser  # optional
```

Open:
👉 http://127.0.0.1:8000/api/docs

ℹ️ Local (venv) setup is documented below for non-Docker users.

---

## 🚀 Features

### **Worldbuilding Entities**
The API supports full CRUD for:

- **Stories**
- **Characters**
- **Locations**
- **Factions**
- **Items**

These entities can reference each other, forming a structured and interconnected world.

### **Stories**
- Hierarchical nesting (`parent` + `order`)
- Rich text fields (title, summary, body)
- Ownership control (`created_by`)
- Visibility system (`private`, `public`, `draft`, `archived`)
- Automatic slug generation

### **Relationships**
Each story can reference:

- Characters
- Locations
- Factions
- Items

And each entity can appear in many stories.

### **Authentication & Users**
- Custom user model (email-based login)
- Endpoints for:
  - User registration
  - Token-based authentication
  - Retrieving/updating the authenticated user's profile

---

## 🏗 Architecture Overview

LoreSmith is designed as a modular Django REST backend with explicit separation
between domain logic, user/auth concerns, and external AI dependencies.

- Django REST Framework API exposing CRUD endpoints
- Core domain logic isolated in `core` app
- User/auth concerns isolated in `user` app
- AI analysis behind a bounded client with safety controls
- Throttling and permissions enforced at the API boundary

This structure allows the API to evolve into async processing (e.g. background AI jobs) without changing external contracts.

---

## 🤖 AI Analysis (POC)

The Story AI endpoint allows users to analyze story content using an OpenAI-powered assistant.

### **Endpoint**
`POST /stories/{id}/analyze/`

### **Output includes:**
- Short summary
- Thematic analysis
- Tone description
- Strengths
- Weaknesses
- Suggestions for improvement
- Token usage metadata

### **Modes**
| Mode | Condition | Description |
|------|-----------|-------------|
| **Mock mode** | AI disabled or no API key | Free, safe development mode with placeholder output |
| **Live mode** | AI enabled + valid API key | Real GPT-4.1-mini analysis |

### **AI Safety**
- Per-user throttling
- Daily token budget enforcement
- Max input character limit
- Max output token limit

AI functionality is intentionally constrained to demonstrate **safe LLM integration patterns** in a backend system.

---

## 🧭 API Tour (5-Minute Overview)

```bash
# 1) Authenticate (get token)
curl -X POST http://127.0.0.1:8000/api/user/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# → Save the returned token for the next requests


# 2) Create a story
curl -X POST http://127.0.0.1:8000/api/stories/ \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My World","summary":"A forgotten land on the edge of time","body":"Long ago..."}'


# 3) List stories
curl -H "Authorization: Token <TOKEN>" \
  http://127.0.0.1:8000/api/stories/


# 4) Analyze a story with AI (POC)
curl -X POST http://127.0.0.1:8000/api/stories/1/analyze/ \
  -H "Authorization: Token <TOKEN>"


# 5) Retrieve the story again (story data is unchanged;
# AI analysis is returned on-demand)
curl -H "Authorization: Token <TOKEN>" \
  http://127.0.0.1:8000/api/stories/1/

```

By default, the AI endpoint runs in mock mode unless OPENAI_API_KEY is set and LORESMITH_AI_ENABLED=true.
Mock mode returns deterministic placeholder output for safe development.

---

## 📦 Project Structure

```text
loresmith-api/
│
├── app/
│   ├── app/                # Django project settings and root URLs
│   ├── core/               # Core domain logic (stories, world entities, AI, permissions)
│   ├── tests/              # Core app tests
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── throttling.py
│   │   ├── ai_client.py
│   │   └── views/
│   │       ├── story.py
│   │       ├── character.py
│   │       ├── location.py
│   │       ├── faction.py
│   │       └── item.py
│   │
│   └── user/               # User API (registration, auth, user profile)
│       ├── tests/          # User app tests
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
│
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🔧 Installation (Local / Venv)

### 1️⃣ Clone the repository

```bash
git clone https://github.com/BenjaminKag/loresmith-api.git
cd loresmith-api
```

### 2️⃣ (Optional) Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate     # Linux/macOS
venv\Scripts\activate        # Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Create your `.env` file

```bash
cp .env.example .env
```

Fill in required fields:

```env
DEBUG=True
SECRET_KEY=changeme

# --- AI / OpenAI ---
OPENAI_API_KEY=changeme
LORESMITH_AI_MODEL=gpt-4.1-mini
LORESMITH_MAX_OUTPUT_TOKENS=256
LORESMITH_MAX_INPUT_CHARS=8000
LORESMITH_DAILY_TOKEN_BUDGET=50000
LORESMITH_AI_ENABLED=true
```

### 5️⃣ Apply migrations

```bash
python manage.py migrate
```

### 6️⃣ Run the server

```bash
python manage.py runserver
```

View docs at:
👉 **http://127.0.0.1:8000/api/docs**

---

## 🧪 Running Tests

Run the test suite:

```bash
pytest
```

Test coverage includes:

- Story, Character, Location, Faction and Item models + CRUD
- Ownership + permissions
- AI endpoint behavior (mocked AI)
- Slug generation
- Related entities CRUD
- User API behavior (registration, auth, profile)

Linting is enforced via `flake8` (CI-ready).

---

## 📚 API Endpoints

> **Note:** These paths assume your global API prefix is `/api/`
> (e.g. `/api/stories/`, `/api/user/create/`).
> Adjust if your URL configuration differs.

### **Stories**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stories/` | List stories |
| POST | `/stories/` | Create story |
| GET | `/stories/{id}/` | Retrieve story |
| PATCH | `/stories/{id}/` | Update story |
| DELETE | `/stories/{id}/` | Delete story |
| POST | `/stories/{id}/analyze/` | **AI-powered story analysis** |

Full endpoint list is available in Swagger.

---

### **Users & Authentication**

User-related endpoints (from the `user` app) are typically mounted under `/api/user/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/user/create/` | Register a new user |
| POST | `/user/token/` | Obtain auth token (login) |
| GET | `/user/me/` | Get the authenticated user's profile |
| PATCH | `/user/me/` | Update the authenticated user's profile |

Authentication is token-based (DRF Token/Auth or similar, depending on your settings).
You can interact with these endpoints via Swagger or any HTTP client (curl, HTTPie, Postman, etc.).

---

## 🧠 AI Configuration Details

### **Mock Mode**
Mock mode activates when:

- `LORESMITH_AI_ENABLED = false`, **or**
- `OPENAI_API_KEY` is missing/empty

Mock mode returns a static AI response for safe development.

### **Live Mode**
Requires:

```env
LORESMITH_AI_ENABLED=true
OPENAI_API_KEY=your-key
```

The system will:

- Call OpenAI's Chat Completion API
- Parse structured JSON output
- Report token usage
- Enforce safety and rate limits

---

## 📝 License
© 2025 Benjamin Kagansky
All Rights Reserved.

This codebase is proprietary. Unauthorized copying, modification,
distribution, or use is strictly prohibited without explicit permission.

---

## 🙌 Credits

Developed by **Benjamin Kagansky**
Backend architecture and AI integration developed with AI-assisted tools.
