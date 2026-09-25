// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title VouchReputation
 * @notice Phase 3: native on-chain reputation for the Vouch platform.
 *
 * The Vouch backend is the single writer (owner). It periodically publishes:
 *  1. Commitment-hash Merkle roots (same flow as VouchAnchor, kept for
 *     compatibility), and
 *  2. Reputation score attestations: the backend signs
 *     keccak256(abi.encode(user, score, observedAt)) with its EIP-191 key and
 *     this contract stores the score + signature. Anyone can verify the
 *     signature on-chain, so a user's published reputation is provably
 *     backend-attested without trusting a UI claim.
 */
contract VouchReputation {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    // NOTE: inclusion proofs use fixed-order pairing — keccak256(left ++ right) —
    // to match the backend's canonical Merkle builder exactly. OZ's MerkleProof
    // sorts each pair before hashing, which yields different roots whenever a
    // node's children are in descending order.

    event ReputationAttested(
        address indexed user,
        int256 score,
        uint256 observedAt,
        uint256 updatedAt
    );
    event BatchAnchored(bytes32 indexed merkleRoot, uint256 batchId, uint256 timestamp);

    address public owner;
    uint256 public nextBatchId;

    // Commitment-hash batch anchoring (VouchAnchor compatibility)
    mapping(uint256 => bytes32) public batchRoots;
    mapping(bytes32 => uint256) public rootToBatchId;

    // Reputation attestations
    struct Attestation {
        int256 score;
        uint256 observedAt;   // point-in-time the score reflects
        uint256 updatedAt;    // block timestamp of the last write
        bytes signature;      // EIP-191 signature over the attestation digest
    }
    mapping(address => Attestation) public attestations;

    error OnlyOwner();
    error InvalidSignature();

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    constructor() {
        owner = msg.sender;
        nextBatchId = 1;
    }

    // ─────────────────────────────────────────────
    // Commitment batch anchoring
    // ─────────────────────────────────────────────

    function anchorBatch(bytes32 merkleRoot) external onlyOwner {
        require(rootToBatchId[merkleRoot] == 0, "Root already anchored");
        batchRoots[nextBatchId] = merkleRoot;
        rootToBatchId[merkleRoot] = nextBatchId;
        emit BatchAnchored(merkleRoot, nextBatchId, block.timestamp);
        nextBatchId++;
    }

    function verifyRoot(bytes32 merkleRoot) external view returns (bool) {
        return rootToBatchId[merkleRoot] != 0;
    }

    // ─────────────────────────────────────────────
    // Reputation attestations
    // ─────────────────────────────────────────────

    function attestationDigest(address user, int256 score, uint256 observedAt)
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(user, score, observedAt));
    }

    /**
     * @notice Publish (or update) a user's reputation score.
     * @param user        The subject address.
     * @param score       Reputation score (can be negative).
     * @param observedAt  Unix seconds the score reflects.
     * @param signature   EIP-191 signature by the owner over the digest.
     */
    function attestReputation(address user, int256 score, uint256 observedAt, bytes calldata signature)
        external
        onlyOwner
    {
        bytes32 digest = attestationDigest(user, score, observedAt);
        bool valid = digest.toEthSignedMessageHash().recover(signature) == owner;
        require(valid, "Invalid signature");

        Attestation storage a = attestations[user];
        a.score = score;
        a.observedAt = observedAt;
        a.updatedAt = block.timestamp;
        a.signature = signature;

        emit ReputationAttested(user, score, observedAt, block.timestamp);
    }

    /**
     * @notice Verify a stored attestation against its stored signature.
     * @return ok True if the stored signature recovers to the owner.
     */
    function verifyAttestation(address user) external view returns (bool ok) {
        Attestation storage a = attestations[user];
        if (a.signature.length == 0) return false;
        bytes32 digest = attestationDigest(user, a.score, a.observedAt);
        return digest.toEthSignedMessageHash().recover(a.signature) == owner;
    }

    /**
     * @notice Read the full attestation record for a user.
     */
    function getAttestation(address user)
        external
        view
        returns (int256 score, uint256 observedAt, uint256 updatedAt, bytes memory signature)
    {
        Attestation storage a = attestations[user];
        return (a.score, a.observedAt, a.updatedAt, a.signature);
    }

    /**
     * @notice Prove a commitment hash was included in an anchored batch.
     * @param root   A previously anchored Merkle root.
     * @param leaf   The commitment content hash (32 bytes).
     * @param proof  The Merkle proof siblings, bottom-up (fixed-order pairing).
     */
    function verifyInclusion(bytes32 root, bytes32 leaf, bytes32[] calldata proof)
        external
        pure
        returns (bool)
    {
        bytes32 computed = leaf;
        for (uint256 i = 0; i < proof.length; ++i) {
            computed = _hashPair(computed, proof[i]);
        }
        return computed == root;
    }

    function _hashPair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(a, b));
    }
}
