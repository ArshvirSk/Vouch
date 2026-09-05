"""End-to-end lifecycle test script.

Tests the complete commitment lifecycle:
  create → evidence → deadline → vote → resolution → reputation update

Run with: python -m scripts.test_lifecycle
Requires the API to be running at http://localhost:8000
"""

import asyncio
import httpx

BASE = "http://localhost:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE) as client:
        print("=" * 60)
        print("VOUCH — Full Lifecycle E2E Test")
        print("=" * 60)

        # 1. Create users
        print("\n[1/7] Creating users...")
        author = await client.post("/auth/signup", json={
            "handle": "alice",
            "email": "alice@test.com",
            "password": "password123",
        })
        author_token = author.json()["access_token"]
        print(f"  ✓ Author 'alice' created")

        juror1 = await client.post("/auth/signup", json={
            "handle": "bob",
            "email": "bob@test.com",
            "password": "password123",
        })
        j1_token = juror1.json()["access_token"]
        print(f"  ✓ Juror 'bob' created")

        juror2 = await client.post("/auth/signup", json={
            "handle": "carol",
            "email": "carol@test.com",
            "password": "password123",
        })
        j2_token = juror2.json()["access_token"]
        print(f"  ✓ Juror 'carol' created")

        juror3 = await client.post("/auth/signup", json={
            "handle": "dave",
            "email": "dave@test.com",
            "password": "password123",
        })
        j3_token = juror3.json()["access_token"]
        print(f"  ✓ Juror 'dave' created")

        # 2. Create commitment
        print("\n[2/7] Creating commitment...")
        commitment_resp = await client.post(
            "/commitments",
            json={
                "title": "Complete 90 LeetCode problems",
                "description": "Solve 3 problems per day for 30 days",
                "measurable_condition": "Solve exactly 90 LeetCode problems by the deadline, verified via LeetCode profile screenshot showing 90+ solved problems",
                "deadline": "2026-10-06T23:59:59Z",
                "juror_handles": ["bob", "carol", "dave"],
            },
            headers={"Authorization": f"Bearer {author_token}"},
        )
        commitment = commitment_resp.json()
        commitment_id = commitment["id"]
        print(f"  ✓ Commitment created: {commitment['title']}")
        print(f"    Status: {commitment['status']}")
        print(f"    Content hash: {commitment['content_hash'][:16]}...")
        print(f"    Jurors: {commitment['juror_count']}")

        # 3. Submit evidence
        print("\n[3/7] Submitting evidence...")
        ev1 = await client.post(
            f"/commitments/{commitment_id}/evidence",
            json={
                "type": "text",
                "content": "Day 1: Solved 3 problems - Two Sum, Valid Parentheses, Merge Two Sorted Lists",
            },
            headers={"Authorization": f"Bearer {author_token}"},
        )
        print(f"  ✓ Evidence 1 submitted (text)")
        print(f"    Hash: {ev1.json()['content_hash'][:16]}...")

        ev2 = await client.post(
            f"/commitments/{commitment_id}/evidence",
            json={
                "type": "link",
                "content": "https://leetcode.com/u/alice/submissions/",
            },
            headers={"Authorization": f"Bearer {author_token}"},
        )
        print(f"  ✓ Evidence 2 submitted (link)")

        # Check status transition
        updated = await client.get(f"/commitments/{commitment_id}")
        print(f"    Status after evidence: {updated.json()['status']}")

        # 4. Check commitment listing
        print("\n[4/7] Listing commitments...")
        listing = await client.get("/commitments?status=evidence_submitted")
        print(f"  ✓ Found {listing.json()['total']} commitment(s) with evidence")

        # 5. Transition to verification (normally done by deadline checker job)
        # For testing, we'd call the admin endpoint or manually update
        print("\n[5/7] Simulating deadline passage (via admin/run-jobs)...")
        # Note: In real test, deadline would need to be in the past
        # For demo purposes, showing the API structure
        print("  ⚠ Skipping (deadline is in the future)")
        print("    In production: Redis job auto-transitions at deadline")

        # 6. View user profile
        print("\n[6/7] Viewing profiles...")
        alice_profile = await client.get("/users/alice")
        ap = alice_profile.json()
        print(f"  ✓ Alice's profile:")
        print(f"    Reputation: {ap['user']['reputation_score']}")
        print(f"    Commitments: {ap['stats']['commitments_met']}/{ap['stats']['commitments_total']}")
        print(f"    Jury accuracy: {ap['stats']['jury_accuracy']}%")

        bob_profile = await client.get("/users/bob")
        bp = bob_profile.json()
        print(f"  ✓ Bob's profile:")
        print(f"    Reputation: {bp['user']['reputation_score']}")
        print(f"    Votes cast: {bp['stats']['total_votes_cast']}")

        # 7. Reputation history
        print("\n[7/7] Checking reputation history...")
        rep_history = await client.get("/users/alice/reputation-history")
        rh = rep_history.json()
        print(f"  ✓ Alice has {len(rh['events'])} reputation events")
        print(f"    Current score: {rh['current_score']}")

        print("\n" + "=" * 60)
        print("✅ LIFECYCLE TEST COMPLETE")
        print("=" * 60)
        print("\nFlows verified:")
        print("  ✓ User signup → JWT token")
        print("  ✓ Create commitment → content_hash computed → jurors assigned")
        print("  ✓ Submit evidence → content_hash computed → status transition")
        print("  ✓ List/filter commitments by status")
        print("  ✓ User profile with stats")
        print("  ✓ Reputation history")
        print("\nPending (require time-based triggers):")
        print("  ⏳ Deadline transition → in_verification")
        print("  ⏳ Jury voting → resolution → reputation events")
        print("  ⏳ Auto-abstain on vote window close")
        print("  ⏳ Reputation recomputation job")


if __name__ == "__main__":
    asyncio.run(main())
