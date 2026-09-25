/**
 * Ethereum Attestation Service (EAS) configuration — Base Sepolia.
 *
 * The Vouch reputation schema encodes: "uint256 reputationScore, string handle"
 *
 * To get a real schema UID:
 *   1. Fund a Base Sepolia wallet (e.g. the Coinbase or Alchemy faucet).
 *   2. Run: cd frontend && DEPLOYER_PRIVATE_KEY=0x... node scripts/registerSchema.js
 *   3. Copy the printed UID into NEXT_PUBLIC_VOUCH_SCHEMA_UID in .env.local.
 *
 * Until then the zero UID below is used as a dev placeholder — attestations
 * created against it will be rejected by the EAS contract at runtime, so the
 * profile page treats attestation failures as non-fatal.
 */
export const EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"; // Base Sepolia
export const SCHEMA_REGISTRY_ADDRESS = "0x4200000000000000000000000000000000000020"; // Base Sepolia
export const VOUCH_SCHEMA = "uint256 reputationScore, string handle";

const ZERO_UID = "0x0000000000000000000000000000000000000000000000000000000000000000";

export const VOUCH_SCHEMA_UID: string =
  process.env.NEXT_PUBLIC_VOUCH_SCHEMA_UID ?? ZERO_UID;

export const isSchemaRegistered = VOUCH_SCHEMA_UID !== ZERO_UID;
