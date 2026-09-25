"""Unit tests for audit fixes — no DB required.

Covers:
- Merkle root construction (anchor task)
- CommitmentCreate jury validation (schemas)
- Falsifiability heuristic + LLM-disabled path (services)

Run: python -m pytest tests/ -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas import CommitmentCreate, FalsifiabilityResult
from app.tasks.anchor import _build_merkle_root
from app.services import falsifiability


# ──────────────────────────────────────────────
# Merkle root (anchor task)
# ──────────────────────────────────────────────

class TestMerkleRoot:
    def test_single_leaf_root_is_leaf(self):
        leaf = "ab" * 32
        assert _build_merkle_root([leaf]) == leaf

    def test_two_leaves_root_is_pair_hash(self):
        import hashlib

        a, b = "11" * 32, "22" * 32
        expected = hashlib.sha256(bytes.fromhex(a) + bytes.fromhex(b)).hexdigest()
        assert _build_merkle_root([a, b]) == expected

    def test_three_leaves_uses_padding(self):
        import hashlib

        a, b, c = "11" * 32, "22" * 32, "33" * 32
        # Odd level → last leaf duplicated, then paired
        expected = hashlib.sha256(
            hashlib.sha256(bytes.fromhex(a) + bytes.fromhex(b)).digest()
            + hashlib.sha256(bytes.fromhex(c) + bytes.fromhex(c)).digest()
        ).hexdigest()
        assert _build_merkle_root([a, b, c]) == expected

    def test_root_is_32_bytes_hex(self):
        leaves = [f"{i:02x}" * 32 for i in range(5)]
        root = _build_merkle_root(leaves)
        assert len(root) == 64
        bytes.fromhex(root)  # must be valid hex

    def test_order_matters(self):
        a, b = "11" * 32, "22" * 32
        assert _build_merkle_root([a, b]) != _build_merkle_root([b, a])

    def test_empty_leaves_raise(self):
        with pytest.raises(ValueError):
            _build_merkle_root([])

    def test_root_matches_batch_of_real_hashes(self):
        import hashlib

        # Simulate the actual job: leaves are sha256 content hashes
        leaves = [hashlib.sha256(f"commitment-{i}".encode()).hexdigest() for i in range(4)]
        root = _build_merkle_root(leaves)
        assert root != hashlib.sha256("".join(leaves).encode()).hexdigest()  # not the old naive hash


# ──────────────────────────────────────────────
# CommitmentCreate jury validation (schemas TODO)
# ──────────────────────────────────────────────

def _commitment_kwargs(**overrides):
    kwargs = {
        "title": "Ship the thing",
        "measurable_condition": "Ship exactly 3 features by 2026-12-01, verified on the board",
        "deadline": "2026-12-01T00:00:00Z",
    }
    kwargs.update(overrides)
    return kwargs


class TestCommitmentCreateValidation:
    def test_private_with_2_to_5_jurors_passes(self):
        for n in (2, 3, 5):
            c = CommitmentCreate(**_commitment_kwargs(juror_handles=[f"u{i}" for i in range(n)]))
            assert len(c.juror_handles) == n

    def test_private_with_too_few_jurors_rejected(self):
        with pytest.raises(ValueError, match="2-5 jurors"):
            CommitmentCreate(**_commitment_kwargs(juror_handles=["only-one"]))

    def test_private_with_too_many_jurors_rejected(self):
        with pytest.raises(ValueError, match="2-5 jurors"):
            CommitmentCreate(**_commitment_kwargs(juror_handles=[f"u{i}" for i in range(6)]))

    def test_public_requires_jury_pool_size(self):
        with pytest.raises(ValueError, match="jury_pool_size"):
            CommitmentCreate(**_commitment_kwargs(is_public=True))

    def test_public_with_pool_size_and_no_handles_passes(self):
        c = CommitmentCreate(**_commitment_kwargs(is_public=True, jury_pool_size=5))
        assert c.is_public and c.jury_pool_size == 5 and c.juror_handles == []

    def test_public_pool_size_below_3_rejected(self):
        with pytest.raises(ValueError):
            CommitmentCreate(**_commitment_kwargs(is_public=True, jury_pool_size=2))


# ──────────────────────────────────────────────
# Falsifiability heuristic (LLM-disabled path)
# ──────────────────────────────────────────────

class TestFalsifiabilityHeuristic:
    def test_vague_condition_rejected(self):
        result = falsifiability.check_falsifiability("be better")
        assert result.is_falsifiable is False
        assert "vague" in result.reason.lower()

    def test_short_condition_rejected(self):
        result = falsifiability.check_falsifiability("run")
        assert result.is_falsifiable is False

    def test_specific_condition_accepted_when_llm_disabled(self):
        # LLM is disabled in the test env → heuristic verdict stands
        result = falsifiability.check_falsifiability(
            "Solve exactly 90 LeetCode problems by 2026-12-01, verified by profile screenshot"
        )
        assert result.is_falsifiable is True
        assert "Mocked" not in result.reason  # the old misleading message is gone
