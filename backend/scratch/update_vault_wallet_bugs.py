import os
from datetime import datetime

vault_path = r"C:\ASK_Main\ObsidianVault\Dev-Brain"
project_name = "Vouch"
date_str = datetime.now().strftime("%Y-%m-%d")

# BUG 001
bug1_content = f"""---
title: BUG-001-Privy-JWKS-Verification-404
date: {date_str}
project: [[{project_name}]]
status: resolved
tags: [bug, auth, privy]
---

# 🐛 BUG-001-Privy-JWKS-Verification-404

## Symptom
> What's actually happening? Error message, unexpected behavior.
Token verification fails with `Invalid token: Fail to fetch data from the url, err: "HTTP Error 403: Forbidden"` or `404 Not Found`.

## Environment
- Stack/version: FastAPI, PyJWT, Privy Auth
- Reproduces on: Backend token verification (`/auth/sync`)

## Steps to reproduce
1. Attempt to decode a Privy JWT using `PyJWKClient("https://auth.privy.io/api/v1/jwks")`.
2. Observe HTTP 403 (due to missing User-Agent) or 404 (due to wrong URL path).

## Investigation
- Privy's JWKS endpoint requires the specific `APP_ID` in the path, and explicitly needs the `.json` extension to bypass Cloudflare anti-bot checks if you don't use a browser User-Agent.

## Root cause
> Fill in once found.
Using the generic JWKS URL or omitting the `.json` extension caused Privy's API/Cloudflare to block the request.

## Fix
```python
# Updated to lazily inject the APP_ID and specifically request jwks.json
jwks_url = f"https://auth.privy.io/api/v1/apps/{{settings.privy_app_id}}/jwks.json"
jwks_client = PyJWKClient(jwks_url)
```

## Prevention
> How do we stop this class of bug from happening again?
Always use `.json` endpoints for server-to-server JWKS fetching when available, as it implies an API client rather than a browser.

## Related
- Caused by / linked to: [[ADR-005-Migrate-to-Privy-Auth]]
- Similar bugs: N/A
"""

# BUG 002
bug2_content = f"""---
title: BUG-002-Privy-Auth-Migration-Conflict
date: {date_str}
project: [[{project_name}]]
status: resolved
tags: [bug, auth, database]
---

# 🐛 BUG-002-Privy-Auth-Migration-Conflict

## Symptom
> What's actually happening? Error message, unexpected behavior.
Logging in with Privy using an email that already existed from the previous Supabase integration throws `Failed to create user (maybe email/wallet conflict)` (HTTP 500/400).

## Environment
- Stack/version: FastAPI, SQLAlchemy, PostgreSQL
- Reproduces on: `/auth/sync` endpoint after migrating from Supabase to Privy.

## Steps to reproduce
1. Have an existing user in the database created via Supabase (has an email, but `privy_id` is null).
2. Log in with Privy using the same email address.
3. The backend tries to create a new user (since `privy_id` doesn't match) and fails due to the `email` unique constraint.

## Investigation
- The original `/auth/sync` logic only queried `User.privy_id == privy_id`. 
- When it didn't find the `privy_id`, it tried to insert a new row, violating the unique index on `email`.

## Root cause
> Fill in once found.
Lack of a seamless migration path for legacy users matching by email.

## Fix
```python
    # Legacy migration: check if user exists by email or wallet
    if request.email:
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()
        
    if user:
        # Migrate the existing user to Privy
        user.privy_id = privy_id
        user.auth_provider = "privy"
        await db.commit()
```

## Prevention
> How do we stop this class of bug from happening again?
When migrating auth providers, always implement an identifier fallback (like email) to seamlessly attach the new provider ID to existing accounts.

## Related
- Caused by / linked to: [[ADR-005-Migrate-to-Privy-Auth]]
- Similar bugs: N/A
"""

# Write files
bugs_dir = os.path.join(vault_path, "04-Bugs", project_name)
os.makedirs(bugs_dir, exist_ok=True)

with open(os.path.join(bugs_dir, "BUG-001-Privy-JWKS-Verification-404.md"), "w", encoding="utf-8") as f:
    f.write(bug1_content)

with open(os.path.join(bugs_dir, "BUG-002-Privy-Auth-Migration-Conflict.md"), "w", encoding="utf-8") as f:
    f.write(bug2_content)

# Update Vouch log
project_file = os.path.join(vault_path, "01-Projects", project_name, f"{project_name}.md")
with open(project_file, "a", encoding="utf-8") as f:
    f.write(f"\n- **{date_str}**: Fixed Privy JWT verification (`BUG-001-Privy-JWKS-Verification-404`) and implemented legacy auth migration (`BUG-002-Privy-Auth-Migration-Conflict`).")
    f.write(f"\n- **{date_str}**: Added Embedded Wallet section to user Profile page to allow exporting Web3 keys.\n")

print("Vault updated successfully.")
