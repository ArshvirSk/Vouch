import os
from web3 import Web3
from eth_account import Account
import logging
from hexbytes import HexBytes

logger = logging.getLogger(__name__)

# RPC configuration
RPC_URL = os.getenv("POLYGON_AMOY_RPC_URL", "https://rpc-amoy.polygon.technology")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ANCHOR_CONTRACT_ADDRESS = os.getenv("ANCHOR_CONTRACT_ADDRESS")

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
            self.contract = self.w3.eth.contract(address=ANCHOR_CONTRACT_ADDRESS, abi=ANCHOR_ABI)

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

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        tx = self.contract.functions.anchorBatch(root_bytes).build_transaction({
            'chainId': 80002, # Polygon Amoy testnet
            'gas': 100000,
            'maxFeePerGas': self.w3.to_wei('2', 'gwei'),
            'maxPriorityFeePerGas': self.w3.to_wei('1', 'gwei'),
            'nonce': nonce,
        })

        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

        # Send transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"Anchored batch root {root_hash} in tx {tx_hash.hex()}")
        return tx_hash.hex()

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

web3_service = Web3Service()
