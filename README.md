# Vouch

Vouch is a decentralized, AI-assisted accountability platform. It provides a core primitive — **commitment → evidence → community verification → reputation** — that powers personal accountability, governance accountability, and public-figure tracking.

## Overview

Vouch is a fully-featured platform supporting **personal peer accountability**, **DAO governance tracking**, and **public-figure accountability**:
- **Commitments**: Users state specific claims, or AI extracts promises automatically from public transcripts.
- **AI Integration**: Google Gemini evaluates claims for falsifiability, extracts concrete promises from speeches, and detects contradictions in historical statements.
- **Evidence & Verification**: Evidence is submitted and verified by open, reputation-weighted, sybil-resistant juries (or private friend groups).
- **On-chain Reputation & Anchoring**: Reputation scores are cryptographically signed (EIP-191) and attested natively on Polygon Amoy. Commitment batches are anchored on-chain using Merkle trees.

## Tech Stack

- **Frontend**: Next.js (App Router), Privy (Auth), EAS (Ethereum Attestation Service)
- **Backend**: FastAPI (Python), SQLAlchemy, asyncpg, APScheduler
- **Database**: PostgreSQL, Redis
- **AI**: Google Gemini API
- **Web3**: Solidity, Hardhat, Polygon Amoy, Web3.py

## Development

The project is split into `frontend`, `backend`, and `contracts` directories.

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires a `.env` file with:
```env
VOUCH_SECRET_KEY=change_me
VOUCH_DATABASE_URL=postgresql+asyncpg://...
VOUCH_GEMINI_API_KEY=your_google_api_key
VOUCH_ENABLE_LLM_CHECK=true
PRIVATE_KEY=0x...
POLYGON_AMOY_RPC_URL=https://rpc-amoy.polygon.technology
REPUTATION_CONTRACT_ADDRESS=0x...
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Requires a `.env.local` file with:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_PRIVY_APP_ID=your_privy_app_id
NEXT_PUBLIC_VOUCH_SCHEMA_UID=0x...
```

### Contracts

```bash
cd contracts
npm install
npx hardhat test
```
To deploy on Polygon Amoy:
```bash
npx hardhat run scripts/deploy.cjs --network polygonAmoy
```

## Documentation

Full product and technical requirements are stored in the `/docs` folder (which is gitignored).
