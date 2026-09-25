from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.routers import commitments, evidence, votes, users, admin, notifications, reports, jury_pool, auth, sources, dao, milestones
from app.jobs.deadline_worker import process_deadlines
from app.tasks.anchor import anchor_pending_commitments
from app.tasks.jury_selection import select_public_juries
from app.tasks.anchor_reputation import anchor_reputations
from app.services.milestone_service import check_milestones

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — starts the deadline scheduler."""
    scheduler.add_job(process_deadlines, "interval", minutes=5, id="deadline_worker")
    scheduler.add_job(select_public_juries, "interval", minutes=15, id="jury_selection")
    scheduler.add_job(anchor_pending_commitments, "interval", minutes=60, id="anchor_batch")
    scheduler.add_job(anchor_reputations, "interval", minutes=60, id="anchor_reputation")
    scheduler.add_job(check_milestones, "interval", minutes=30, id="milestone_check")
    scheduler.start()
    logger.info("Deadline scheduler started (every 5 minutes)")
    logger.info("Jury selection scheduler started (every 15 minutes)")
    logger.info("Batch anchoring scheduler started (every 60 minutes)")
    logger.info("Reputation anchoring scheduler started (every 60 minutes)")
    yield
    scheduler.shutdown()
    logger.info("Deadline scheduler stopped")


app = FastAPI(
    title="Vouch API",
    description="Decentralized accountability platform",
    version="0.5.0",
    lifespan=lifespan,
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(commitments.router)
app.include_router(evidence.router)
app.include_router(votes.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(jury_pool.router)
app.include_router(auth.router)
app.include_router(sources.router)
app.include_router(dao.router)
app.include_router(milestones.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.5.0"}
