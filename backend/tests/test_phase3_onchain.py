"""Phase 3 tests — on-chain reputation, DAO ingestion models, jury weighting.

The web3 signing tests run against a locally generated key (no RPC needed for
digest/signature math); RPC-dependent calls are skipped when unconfigured.
"""

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.dao import DaoProposal, DaoProposalStatus
from app.schemas import CommitmentCreate
from app.services import jury_weighting


# ──────────────────────────────────────────────
# Attestation digest/signature roundtrip (EIP-191, mirrors the contract)
# ──────────────────────────────────────────────

class TestAttestationSigning:
    def test_digest_matches_contract_encoding(self):
        from eth_abi import encode as abi_encode
        from web3 import Web3

        from app.services.web3 import Web3Service

        addr = "0x1234567890AbcdEF1234567890aBcdef12345678"
        digest = Web3Service.attestation_digest(addr, 8742, 1700000000)
        expected = Web3.keccak(
            abi_encode(["address", "int256", "uint256"], [Web3.to_checksum_address(addr), 8742, 1700000000])
        )
        assert digest == expected
        assert len(digest) == 32

    def test_signature_recovers_to_signer(self):
        from eth_account import Account
        from eth_account.messages import encode_defunct

        from app.services.web3 import Web3Service

        key = Account.create().key
        svc = Web3Service.__new__(Web3Service)  # bypass __init__ (no RPC)
        svc.account = Account.from_key(key)
        svc.w3 = None
        svc.contract = None
        svc.reputation_contract = None

        addr = "0x1234567890AbcdEF1234567890aBcdef12345678"
        sig = svc.build_attestation_signature(addr, 8742, 1700000000)

        digest = Web3Service.attestation_digest(addr, 8742, 1700000000)
        recovered = Account.recover_message(encode_defunct(digest), signature=sig)
        assert recovered == Account.from_key(key).address

    def test_score_scaling_keeps_two_decimals(self):
        # 87.42 * 100 → 8742 basis points
        score = 87.42
        assert int(round(score * 100)) == 8742
        assert 8742 / 100.0 == pytest.approx(87.42)


# ──────────────────────────────────────────────
# DAO proposal model constraints
# ──────────────────────────────────────────────

class TestDaoProposalModel:
    def test_status_enum_values(self):
        assert DaoProposalStatus.PENDING.value == "pending"
        assert DaoProposalStatus.IMPORTED.value == "imported"
        assert DaoProposalStatus.REJECTED.value == "rejected"

    def test_tablename(self):
        assert DaoProposal.__tablename__ == "dao_proposals"


# ──────────────────────────────────────────────
# Reputation-weighted jury selection math
# ──────────────────────────────────────────────

class TestJuryWeighting:
    def test_reputation_bonus_squashes_large_scores(self):
        # sqrt squashing: 10000 rep → bonus 100, not 10000
        assert jury_weighting.reputation_bonus(10000.0) == pytest.approx(100.0)
        assert jury_weighting.reputation_bonus(0.0) == 0.0

    def test_negative_reputation_gives_no_bonus(self):
        assert jury_weighting.reputation_bonus(-50.0) == 0.0

    def test_weight_floors_at_one(self):
        assert jury_weighting.juror_weight(0.0, 0.0) == 1.0
        assert jury_weighting.juror_weight(-10.0, -5.0) == 1.0

    def test_weight_combines_stake_and_reputation(self):
        # stake 5 + sqrt(100)=10 → 15
        assert jury_weighting.juror_weight(5.0, 100.0) == pytest.approx(15.0)

    def test_higher_reputation_gets_higher_weight(self):
        assert jury_weighting.juror_weight(0.0, 400.0) > jury_weighting.juror_weight(0.0, 100.0)

    def test_weighted_draw_without_replacement_respects_bounds(self):
        class Entry:
            def __init__(self, user_id):
                self.user_id = user_id

        entries = [Entry(i) for i in range(5)]
        weights = [1.0, 1.0, 1.0, 1.0, 1.0]
        picked = jury_weighting.weighted_pick_without_replacement(entries, weights, 3)
        assert len(picked) == 3
        assert len({e.user_id for e in picked}) == 3  # no duplicates
