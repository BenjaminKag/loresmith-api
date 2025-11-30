# Django API Template

A minimal, Dockerized starting point for building Django REST API projects with PostgreSQL and Redis.

This repository is meant to be cloned and adapted for **new projects**, so it contains only the infrastructure and a barebones app structure – no domain logic.

---

## Features

- Django 5 + Django REST Framework
- PostgreSQL database (via Docker)
- Redis cache (via `django-redis`)
- Docker Compose for local development
- Basic GitHub Actions workflow (tests + flake8)
- Example `.env.example` for environment variables
- Placeholder tests and module stubs ready to extend

---

## Requirements

- Docker & Docker Compose
- Git
- (Optional) Python 3.11+ if you want to run Django outside Docker

---

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url> django-api-template
cd django-api-template
```

### 2. Environment variables

Copy the example env file and adjust if needed:

```bash
cp .env.example .env
```

### 3. Run with Docker

```bash
docker compose up --build
```

### 4. Stop

```bash
docker compose down
```

---

## Running Tests & Lint

```bash
docker compose run --rm app sh -c "python manage.py wait_for_db && python manage.py test"
docker compose run --rm app sh -c "flake8"
```

---

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── checks.yml
├── app/
│   ├── manage.py
│   ├── .flake8
│   ├── app/
│   └── core/
├── scripts/
│   └── .gitkeep
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements.dev.txt
└── README.md
```

---

## Using This Template

1. Clone or copy into a new project folder.
2. Update README, project name, etc.
3. Add your models, serializers, views inside `core/` or new Django apps.
4. Add real tests under `core/tests/`.

---

## CI Reminder: Docker Hub Credentials

If you later want to push Docker images via GitHub Actions:

1. Uncomment the Docker Hub login step in `.github/workflows/checks.yml`
2. Add secrets:
   - `DOCKERHUB_USER`
   - `DOCKERHUB_TOKEN`

Otherwise, it's safe to keep the step commented out.

---

## License

Add your license here.
