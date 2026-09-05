from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, commitments, evidence, votes, users

app = FastAPI(
    title="Vouch API",
    description="Decentralized accountability platform — MVP Phase 1",
    version="0.1.0",
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers — TRD §5
app.include_router(auth.router)
app.include_router(commitments.router)
app.include_router(evidence.router)
app.include_router(votes.router)
app.include_router(users.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
