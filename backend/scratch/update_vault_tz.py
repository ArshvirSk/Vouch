import os
from datetime import datetime

vault_path = r"C:\ASK_Main\ObsidianVault\Dev-Brain"
project_name = "Vouch"
date_str = datetime.now().strftime("%Y-%m-%d")

# BUG 003
bug3_content = f"""---
title: BUG-003-Timezone-Aware-Datetime-Models
date: {date_str}
project: [[{project_name}]]
status: resolved
tags: [bug, database, sqlalchemy, asyncpg]
---

# 🐛 BUG-003-Timezone-Aware-Datetime-Models

## Symptom
> What's actually happening? Error message, unexpected behavior.
When creating a new user (or any other model instance with a default `created_at` timestamp), SQLAlchemy throws:
`asyncpg.exceptions.DataError: invalid input for query argument $8: datetime.datetime(...) (can't subtract offset-naive and offset-aware datetimes)`

## Environment
- Stack/version: FastAPI, SQLAlchemy, asyncpg, PostgreSQL
- Reproduces on: Row creation (e.g., `POST /auth/sync`)

## Steps to reproduce
1. Attempt to insert a new row in a table using a `created_at` column defined with `datetime.now(timezone.utc)`.

## Investigation
- By default, SQLAlchemy Maps Python `datetime` to PostgreSQL `TIMESTAMP WITHOUT TIME ZONE`.
- Passing an offset-aware datetime (one with `tzinfo` set, like `timezone.utc`) causes `asyncpg` to throw an error because it expects an offset-naive datetime.

## Root cause
> Fill in once found.
Using `datetime.now(timezone.utc)` as the default factory for a timezone-naive SQLAlchemy column.

## Fix
```python
    created_at: Mapped[datetime] = mapped_column(
        # Strip the tzinfo to make it offset-naive while retaining UTC time
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=text("now()"),
    )
```
*Applied to all models: User, Commitment, Evidence, Vote, Notification, ReputationEvent.*

## Prevention
> How do we stop this class of bug from happening again?
Either use `DateTime(timezone=True)` in all SQLAlchemy models, or strictly enforce `replace(tzinfo=None)` or `datetime.utcnow()` (deprecated) for all default factories.

## Related
- Caused by / linked to: N/A
- Similar bugs: The deadline worker had a similar issue when querying.
"""

# Write files
bugs_dir = os.path.join(vault_path, "04-Bugs", project_name)
os.makedirs(bugs_dir, exist_ok=True)

with open(os.path.join(bugs_dir, "BUG-003-Timezone-Aware-Datetime-Models.md"), "w", encoding="utf-8") as f:
    f.write(bug3_content)

# Update Vouch log
project_file = os.path.join(vault_path, "01-Projects", project_name, f"{project_name}.md")
with open(project_file, "a", encoding="utf-8") as f:
    f.write(f"\n- **{date_str}**: Fixed asyncpg offset-aware datetime insertion bug across all SQLAlchemy models (`BUG-003-Timezone-Aware-Datetime-Models`).\n")

print("Vault updated successfully.")
