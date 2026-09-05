# Vouch

Vouch is a decentralized accountability platform. It provides a core primitive — **commitment → evidence → community verification → reputation** — that can power personal accountability, governance accountability, and public-figure tracking.

## Overview

Currently in MVP (Phase 2), Vouch implements the **personal peer accountability** skin:
- **Commitments**: Users state specific, falsifiable claims with deadlines.
- **Evidence**: Users submit proof (text, links) before the deadline.
- **Verification**: A chosen jury of peers votes on whether the commitment was met.
- **Reputation**: Users build a track record (reputation score and streaks) based on commitments kept, and jurors earn reputation for accurate voting.

## Tech Stack

- **Frontend**: Next.js (App Router), React, CSS Modules
- **Backend**: FastAPI (Python), SQLAlchemy, asyncpg
- **Database**: PostgreSQL (Supabase)
- **AI Validation**: Google Gemini API (for commitment falsifiability checks)

## Development

The project is split into `frontend` and `backend` directories.

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires a `.env` file with:
```
VOUCH_SECRET_KEY=...
VOUCH_DB_URL=postgresql+asyncpg://...
GEMINI_API_KEY=...
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Requires a `.env.local` file with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Documentation

Full product and technical requirements are stored in the `/docs` folder (which is gitignored).
