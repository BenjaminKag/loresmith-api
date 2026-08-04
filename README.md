# LoreSmith API

[![Checks](https://github.com/BenjaminKag/loresmith-api/actions/workflows/checks.yml/badge.svg?branch=mvp)](https://github.com/BenjaminKag/loresmith-api/actions/workflows/checks.yml)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary-red)](#-license)

LoreSmith is a **worldbuilding backend API** for writers, game developers, and creative teams.

It helps creators manage complex fictional worlds through structured support for **stories, characters, factions, locations, items, tags, traits, images, and character profiles**, alongside AI-assisted story analysis and character profile generation.

The project focuses on backend architecture, data modeling, permissions, API design, testing, AI workflow safety, and deployment-ready infrastructure.

---

## 📸 Demo & Docs

- **Swagger / OpenAPI UI:** `http://127.0.0.1:8000/api/docs/`
- **Schema:** `http://127.0.0.1:8000/api/schema/`
- **Auth:** Token-based authentication via `/api/user/token/`

All main endpoints are documented and testable through Swagger.

---

## 🚀 Quickstart with Docker

```bash
git clone https://github.com/BenjaminKag/loresmith-api.git
cd loresmith-api
cp .env.example .env
```

```bash
docker compose up --build -d
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser  # optional
```

Open:
👉 http://127.0.0.1:8000/api/docs

---

## Main Features

### Worldbuilding Entities

LoreSmith supports full CRUD APIs for:

- Stories
- Characters
- Locations
- Factions
- Items
- Tags
- Trait sets and traits
- Character profiles
- Story AI analysis records

Entities can be connected to stories, allowing users to build structured fictional worlds with relationships between narrative elements.

---

## Stories

Stories support:

- Hierarchical structure using `parent`, `kind`, and `order`
- Story types such as story, part, and standalone entries
- Public/private visibility
- Ownership-based permissions
- Related characters, locations, factions, and items
- Tags
- Optional story image upload
- Wiki/tree-style story structure endpoints
- AI-powered story analysis

---

## Permissions and Visibility

The API includes ownership and visibility logic across the main entities.

Supported behavior includes:

- Private-by-default user-owned content
- Public story visibility
- Nested story visibility rules
- Anonymous access to public content
- Owner-only editing
- Validation to prevent users from linking their content to objects they do not own or cannot access

This makes the backend closer to a real multi-user product instead of a simple CRUD demo.

---

## Tags

LoreSmith includes user-scoped tags that can be attached to worldbuilding entities.

Tag features include:

- User-owned tags
- Tag normalization
- Tag creation and management
- Tag filtering
- Many-to-many tag support across stories and entities

---

## Trait Sets and Character Profiles

LoreSmith supports structured character profiling through trait sets and traits.

This allows characters to have profile data such as personality, mental traits, physical traits, priorities, and other structured worldbuilding attributes.

Character profile functionality includes:

- Trait sets
- Traits
- Allowed trait sets per story
- Character profiles linked to characters
- Manual profile structure support
- AI-assisted character profile generation

---

## Image Support

LoreSmith supports image uploads for worldbuilding entities.

Supported image fields include:

- Story image
- Character image
- Location image
- Faction image
- Item image

The project supports local media storage for development and S3-backed media storage for production-style deployment.

---

## AI Features

LoreSmith includes AI-assisted backend workflows designed with safety, cost control, and repeatability in mind.

### Story Analysis

The story analysis endpoint can analyze a story and return structured feedback such as:

- Summary
- Thematic analysis
- Tone
- Strengths
- Weaknesses
- Suggestions
- Consistency-oriented feedback
- Token usage metadata

### Character Profile Generation

LoreSmith includes an AI workflow for generating structured character profile suggestions from existing character/story information.

### AI Safety and Cost Controls

The AI system includes:

- Mock mode for safe local development
- Live mode when AI is enabled and an API key is configured
- AI request idempotency
- Duplicate request protection
- AI usage logging
- Token/cost tracking structure
- Premium gating for AI endpoints
- Story analysis cleanup policy
- Configurable limits for input size and output tokens

---

## AI Modes

### Mock Mode

Mock mode is used when AI is disabled or no API key is configured.

This allows development and testing without making real API calls.

### Live Mode

Live mode requires:

```env
LORESMITH_AI_ENABLED=true
OPENAI_API_KEY=your_api_key
```

When enabled, LoreSmith can call the configured AI provider and return structured AI responses.

---

## API Tour

### 1. Create a user

```bash
curl -X POST http://127.0.0.1:8000/api/user/create/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","name":"Test User"}'
```

### 2. Get an auth token

```bash
curl -X POST http://127.0.0.1:8000/api/user/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### 3. Create a story

```bash
curl -X POST http://127.0.0.1:8000/api/stories/ \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Broken Kingdom","summary":"A kingdom divided by ancient magic.","body":"Long ago..."}'
```

### 4. List stories

```bash
curl -H "Authorization: Token <TOKEN>" \
  http://127.0.0.1:8000/api/stories/
```

### 5. Analyze a story

```bash
curl -X POST http://127.0.0.1:8000/api/stories/1/analyze/ \
  -H "Authorization: Token <TOKEN>"
```

---

## Project Structure

```text
loresmith-api/
├── .github/
│   └── workflows/
│       └── checks.yml
│
├── app/
│   ├── app/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── core/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── mixins.py
│   │   ├── admin.py
│   │   ├── throttling.py
│   │   ├── urls.py
│   │   ├── views/
│   │   │   ├── story.py
│   │   │   ├── character.py
│   │   │   ├── location.py
│   │   │   ├── faction.py
│   │   │   ├── item.py
│   │   │   ├── tag.py
│   │   │   └── trait.py
│   │   ├── services/
│   │   │   ├── ai_client.py
│   │   │   ├── ai_idempotency.py
│   │   │   ├── ai_usage.py
│   │   │   ├── character_profile_generator.py
│   │   │   ├── story_analysis_cleanup.py
│   │   │   └── story_analysis_generator.py
│   │   └── tests/
│   │
│   ├── user/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   └── manage.py
│
├── scripts/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements.dev.txt
├── .env.example
├── LICENSE
└── README.md
```

---

## Local Installation without Docker

### 1️⃣ Clone the repository

```bash
git clone https://github.com/BenjaminKag/loresmith-api.git
cd loresmith-api
```

### 2️⃣ Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate     # Linux/macOS
venv\Scripts\activate        # Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Create your environment file

```bash
cp .env.example .env
```

### 5️⃣ Move into the Django app directory

```bash
cd app
```

### 6️⃣ Apply migrations

```bash
python manage.py migrate
```

### 7️⃣ Run the development server

```bash
python manage.py runserver
```

View docs at:
👉 **http://127.0.0.1:8000/api/docs/**

---

## Environment Variables

The project uses environment variables for configuration.

Common variables include:

```env
DEBUG=True
SECRET_KEY=changeme
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

DB_HOST=db
DB_NAME=devdb
DB_USER=devuser
DB_PASS=changeme

CACHE_BACKEND=django_redis.cache.RedisCache
CACHE_LOCATION=redis://redis:6379/1
CACHE_KEY_PREFIX=loresmith_api

USE_S3=False
AWS_STORAGE_BUCKET_NAME=changeme
AWS_S3_REGION_NAME=il-central-1
AWS_S3_CUSTOM_DOMAIN=

LORESMITH_AI_ENABLED=false
OPENAI_API_KEY=
LORESMITH_AI_MODEL=gpt-4.1-mini
LORESMITH_MAX_OUTPUT_TOKENS=256
LORESMITH_MAX_INPUT_CHARS=8000
LORESMITH_DAILY_TOKEN_BUDGET=250000
LORESMITH_USER_DAILY_TOKEN_BUDGET=40000
```

For the full list of supported variables, see `.env.example`.

Note: Production security values such as `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE` should be configured according to the deployment environment.

---

## Running Tests

Run the test suite with Docker:

```bash
docker compose run --rm app sh -c "python manage.py wait_for_db && python manage.py test"
```

Or locally from the `app/` directory:

```bash
python manage.py test
```

The test suite covers:

- User registration and authentication
- Story model and API behavior
- Character, location, faction, and item APIs
- Ownership and permissions
- Public/private visibility rules
- Nested story behavior
- Tags and tag filtering
- Trait sets and traits
- Character profile generation
- Story AI analysis
- AI idempotency
- AI usage logging
- Story analysis cleanup
- Serializer validation
- Management commands

---

## Linting

Run flake8 with Docker:

```bash
docker compose run --rm app sh -c "flake8"
```

---

## Deployment Notes

LoreSmith is built with deployment readiness in mind.

The project includes support for:

- Dockerized application setup
- PostgreSQL database configuration
- Gunicorn production server
- Static file collection
- S3-backed media storage
- Environment-based production settings
- AWS-style deployment configuration

---

## Main Technologies

- Python
- Django
- Django REST Framework
- PostgreSQL
- Docker
- Gunicorn
- drf-spectacular / Swagger
- Pillow
- django-storages
- AWS S3-compatible media storage
- Token authentication
- OpenAI-compatible AI integration

---

## 📝 License

© 2025 Benjamin Kagansky
All Rights Reserved.

This codebase is proprietary. Unauthorized copying, modification, distribution, or use is strictly prohibited without explicit permission.

---

## Credits

Developed by **Benjamin Kagansky**.

Backend architecture, API design, AI workflows, permissions, tests, and deployment preparation were developed as part of the LoreSmith MVP.
