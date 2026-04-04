# FMCG ERP System

A browser-based ERP system for Fast-Moving Consumer Goods companies.

## Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | FastAPI (Python) + asyncpg        |
| Frontend  | Next.js 14 + TypeScript + Tailwind|
| Database  | PostgreSQL 16                     |
| Container | Docker + Docker Compose           |

## Getting Started

### Prerequisites
- Docker & Docker Compose

### Setup

```bash
cp .env.example .env
# Edit .env with your secrets

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
fmcg-erp-system/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Config, security
│   │   ├── db/            # Database session, base model
│   │   ├── models/        # SQLAlchemy models
│   │   └── schemas/       # Pydantic schemas
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # Next.js application
│   ├── src/
│   │   ├── app/           # App Router pages
│   │   ├── components/    # Shared UI components
│   │   └── lib/           # API client, utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## Development

### Backend only
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend only
```bash
cd frontend
npm install
npm run dev
```
