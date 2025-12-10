# LoreSmith API

LoreSmith is a backend API for worldbuilding and storytelling management.
It allows writers, game developers, and creative worldbuilders to organize
stories, characters, factions, locations, and items — while also offering an
AI-powered assistant that analyzes story content and provides structured feedback.

This project represents the **POC (Proof of Concept)** version of the LoreSmith backend.

---

## 🚀 Features

### **Worldbuilding Entities**
The API supports full CRUD for:

- **Stories**
- **Characters**
- **Locations**
- **Factions**
- **Items**

These entities can link to each other, forming a structured and interconnected world.

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

---

## 📚 API Documentation

Interactive Swagger UI:
👉 **http://127.0.0.1:8000/api/docs**

OpenAPI schema is auto-generated via **drf-spectacular**.

---

## 📦 Project Structure

```text
loresmith-api/
│
├── app/
│   ├── app/                # Django project settings and root URLs
│   ├── core/               # Core domain logic (stories, world entities, AI, permissions)
|   ├── tests/              # Core app tests
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
|       ├── tests/          # User app tests
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
│
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🔧 Installation

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

- Story model + CRUD
- Ownership + permissions
- AI endpoint behavior (mocked AI)
- Slug generation
- Related entities CRUD
- User API behavior (registration, auth, profile)

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

---

### **Characters**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/characters/` | List characters |
| POST | `/characters/` | Create character |
| GET | `/characters/{id}/` | Retrieve character |
| PATCH | `/characters/{id}/` | Update character |
| DELETE | `/characters/{id}/` | Delete character |

---

### **Locations**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/locations/` | List locations |
| POST | `/locations/` | Create location |
| GET | `/locations/{id}/` | Retrieve location |
| PATCH | `/locations/{id}/` | Update location |
| DELETE | `/locations/{id}/` | Delete location |

---

### **Factions**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/factions/` | List factions |
| POST | `/factions/` | Create faction |
| GET | `/factions/{id}/` | Retrieve faction |
| PATCH | `/factions/{id}/` | Update faction |
| DELETE | `/factions/{id}/` | Delete faction |

---

### **Items**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/items/` | List items |
| POST | `/items/` | Create item |
| GET | `/items/{id}/` | Retrieve item |
| PATCH | `/items/{id}/` | Update item |
| DELETE | `/items/{id}/` | Delete item |

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
This codebase is proprietary and may not be copied, modified, or distributed without explicit permission.


---

## 🙌 Credits

Developed by **Benjamin Kagansky**
AI integration & backend architecture built with assistance from ChatGPT.
