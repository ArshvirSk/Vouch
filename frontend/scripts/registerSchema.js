/**
 * Registers the Vouch reputation schema with the EAS SchemaRegistry on
 * Base Sepolia and prints the resulting schema UID.
 *
 * Usage:
 *   cd frontend
 *   DEPLOYER_PRIVATE_KEY=0x... node scripts/registerSchema.js
 *
 * Then add the printed UID to frontend/.env.local:
 *   NEXT_PUBLIC_VOUCH_SCHEMA_UID=0x...
 *
 * Requires:
 *   DEPLOYER_PRIVATE_KEY — a funded Base Sepolia testnet key (never a mainnet key!)
 *   BASE_SEPOLIA_RPC_URL — optional, defaults to https://sepolia.base.org
 */
const { SchemaRegistry } = require("@ethereum-attestation-service/eas-sdk");
const { ethers } = require("ethers");
const fs = require("fs");
const path = require("path");

const SCHEMA_REGISTRY_ADDRESS = "0x4200000000000000000000000000000000000020"; // Base Sepolia
const SCHEMA = "uint256 reputationScore, string handle";
const RESOLVER = ethers.ZeroAddress; // no on-chain resolver logic for the MVP
const REVOCABLE = true;

async function main() {
  const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
  if (!privateKey) {
    console.error(
      "Missing DEPLOYER_PRIVATE_KEY env var. Export a funded Base Sepolia test key (never a production key)."
    );
    process.exit(1);
  }

  const rpcUrl = process.env.BASE_SEPOLIA_RPC_URL || "https://sepolia.base.org";
  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const signer = new ethers.Wallet(privateKey, provider);

  const schemaRegistry = new SchemaRegistry(SCHEMA_REGISTRY_ADDRESS);
  schemaRegistry.connect(signer);

  console.log("Registering schema on Base Sepolia...");
  console.log(`  RPC:       ${rpcUrl}`);
  console.log(`  Schema:    ${SCHEMA}`);
  console.log(`  Resolver:  none (zero address)`);
  console.log(`  Revocable: ${REVOCABLE}`);

  // EAS SDK: tx.wait() resolves to the newly created schema UID.
  const tx = await schemaRegistry.register({
    schema: SCHEMA,
    resolverAddress: RESOLVER,
    revocable: REVOCABLE,
  });
  const schemaUID = await tx.wait();

  const outPath = path.join(__dirname, "..", ".schema-uid.json");
  fs.writeFileSync(
    outPath,
    JSON.stringify({ schema: SCHEMA, uid: schemaUID, chain: "base-sepolia" }, null, 2)
  );

  console.log(`\n✅ Schema registered. UID: ${schemaUID}`);
  console.log(`Saved to ${outPath}`);
  console.log(`\nNext step: add to frontend/.env.local →`);
  console.log(`NEXT_PUBLIC_VOUCH_SCHEMA_UID=${schemaUID}`);
}

main().catch((e) => {
  console.error("Schema registration failed:", e?.shortMessage ?? e?.message ?? e);
  process.exit(1);
});
