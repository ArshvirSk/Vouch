import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode as abi_encode
import logging
from hexbytes import HexBytes

logger = logging.getLogger(__name__)

# RPC configuration
RPC_URL = os.getenv("POLYGON_AMOY_RPC_URL", "https://rpc-amoy.polygon.technology")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ANCHOR_CONTRACT_ADDRESS = os.getenv("ANCHOR_CONTRACT_ADDRESS")
REPUTATION_CONTRACT_ADDRESS = os.getenv("REPUTATION_CONTRACT_ADDRESS")

CHAIN_ID = int(os.getenv("CHAIN_ID", "80002"))  # 80002 = Polygon Amoy testnet

# Minimal ABI for VouchAnchor.sol
ANCHOR_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"}],
        "name": "anchorBatch",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"}],
        "name": "verifyRoot",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Minimal ABI for VouchReputation.sol
REPUTATION_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "int256", "name": "score", "type": "int256"},
            {"internalType": "uint256", "name": "observedAt", "type": "uint256"},
            {"internalType": "bytes", "name": "signature", "type": "bytes"},
        ],
        "name": "attestReputation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getAttestation",
        "outputs": [
            {"internalType": "int256", "name": "", "type": "int256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "bytes", "name": "", "type": "bytes"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "verifyAttestation",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _checksum(address: str) -> str:
    return Web3.to_checksum_address(address)


class Web3Service:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))

        if not PRIVATE_KEY:
            logger.warning("PRIVATE_KEY not set. Web3 anchoring will be disabled.")
            self.account = None
        else:
            self.account = Account.from_key(PRIVATE_KEY)

        if not ANCHOR_CONTRACT_ADDRESS:
            logger.warning("ANCHOR_CONTRACT_ADDRESS not set. Web3 anchoring will be disabled.")
            self.contract = None
        else:
            self.contract = self.w3.eth.contract(
                address=_checksum(ANCHOR_CONTRACT_ADDRESS), abi=ANCHOR_ABI
            )

        if not REPUTATION_CONTRACT_ADDRESS:
            logger.warning("REPUTATION_CONTRACT_ADDRESS not set. On-chain reputation will be disabled.")
            self.reputation_contract = None
        else:
            self.reputation_contract = self.w3.eth.contract(
                address=_checksum(REPUTATION_CONTRACT_ADDRESS), abi=REPUTATION_ABI
            )

    # ── shared tx plumbing ──────────────────────────────────

    def _fees(self) -> dict:
        """EIP-1559 fees derived from the chain, not magic numbers.

        maxFee = 2x current base fee + priority fee (priority configurable
        via PRIORITY_FEE_GWEI; Polygon needs a meaningful priority tip).
        """
        try:
            base = self.w3.eth.get_block("latest")["baseFeePerGas"]
        except Exception:
            base = self.w3.to_wei(50, "gwei")
        priority = self.w3.to_wei(float(os.getenv("PRIORITY_FEE_GWEI", "30")), "gwei")
        return {
            "maxFeePerGas": 2 * base + priority,
            "maxPriorityFeePerGas": priority,
        }

    def _send(self, fn_call) -> str:
        """Estimate gas, build, sign and send a transaction from the backend account."""
        if not self.account:
            raise ValueError("Web3 configuration missing (PRIVATE_KEY)")

        # Estimate from the actual call (attestations cost ~190k — a hardcoded
        # cap either wastes gas or fails with 'out of gas')
        try:
            gas = int(fn_call.estimate_gas({"from": self.account.address}) * 1.2)
        except Exception:
            gas = 600_000  # conservative fallback if estimation itself reverts

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = fn_call.build_transaction({
            "chainId": CHAIN_ID,
            "gas": gas,
            **self._fees(),
            "nonce": nonce,
        })
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        # web3.py v7 renamed rawTransaction -> raw_transaction
        raw = getattr(signed_tx, "raw_transaction", None) or signed_tx.rawTransaction
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        return tx_hash.hex()

    # ── commitment batch anchoring ──────────────────────────

    def anchor_merkle_root(self, root_hash: str) -> str:
        """
        Submits a Merkle Root to the VouchAnchor smart contract on Polygon.
        Returns the transaction hash.
        """
        if not self.account or not self.contract:
            logger.error("Web3 service not fully configured.")
            raise ValueError("Web3 configuration missing (PRIVATE_KEY or ANCHOR_CONTRACT_ADDRESS)")

        # Convert root_hash to bytes32 (must be 32 bytes hex string)
        if root_hash.startswith("0x"):
            root_bytes = HexBytes(root_hash)
        else:
            root_bytes = HexBytes(f"0x{root_hash}")

        if len(root_bytes) != 32:
            raise ValueError(f"Invalid root hash length: expected 32 bytes, got {len(root_bytes)}")

        tx_hash = self._send(self.contract.functions.anchorBatch(root_bytes))
        logger.info(f"Anchored batch root {root_hash} in tx {tx_hash}")
        return tx_hash

    def verify_root(self, root_hash: str) -> bool:
        """
        Check if a given root hash was anchored.
        """
        if not self.contract:
            return False

        if root_hash.startswith("0x"):
            root_bytes = HexBytes(root_hash)
        else:
            root_bytes = HexBytes(f"0x{root_hash}")

        return self.contract.functions.verifyRoot(root_bytes).call()

    # ── native on-chain reputation (Phase 3) ────────────────

    @staticmethod
    def attestation_digest(user_address: str, score_scaled: int, observed_at: int) -> bytes:
        """Recreate the contract's digest: keccak256(abi.encode(user, score, observedAt))."""
        return Web3.keccak(
            abi_encode(["address", "int256", "uint256"], [_checksum(user_address), score_scaled, observed_at])
        )

    def build_attestation_signature(self, user_address: str, score_scaled: int, observed_at: int) -> bytes:
        """EIP-191 signature over the attestation digest using the backend key."""
        digest = self.attestation_digest(user_address, score_scaled, observed_at)
        signable = encode_defunct(digest)
        signed = self.account.sign_message(signable) if self.account else None
        if signed is None:
            raise ValueError("Web3 configuration missing (PRIVATE_KEY)")
        return signed.signature

    def attest_reputation(self, user_address: str, score_scaled: int, observed_at: int) -> str:
        """Publish a signed reputation attestation on-chain. Returns the tx hash.

        `score_scaled` is the score in basis points (score * 100) so the
        int256 on-chain value keeps two decimals.
        """
        if not self.account or not self.reputation_contract:
            raise ValueError("Web3 configuration missing (PRIVATE_KEY or REPUTATION_CONTRACT_ADDRESS)")

        signature = self.build_attestation_signature(user_address, score_scaled, observed_at)
        tx_hash = self._send(
            self.reputation_contract.functions.attestReputation(
                _checksum(user_address), score_scaled, observed_at, signature
            ),
        )
        logger.info("Attested reputation %s for %s in tx %s", score_scaled, user_address, tx_hash)
        return tx_hash

    def get_attestation(self, user_address: str) -> dict | None:
        """Read the on-chain attestation for a user (None if never attested)."""
        if not self.reputation_contract:
            return None
        score, observed_at, updated_at, _sig = self.reputation_contract.functions.getAttestation(
            _checksum(user_address)
        ).call()
        if updated_at == 0:
            return None
        return {"score": score / 100.0, "observed_at": observed_at, "updated_at": updated_at}

    def verify_attestation(self, user_address: str) -> bool:
        """On-chain check that the stored signature recovers to the owner."""
        if not self.reputation_contract:
            return False
        return self.reputation_contract.functions.verifyAttestation(_checksum(user_address)).call()


web3_service = Web3Service()
