/**
 * Deploys VouchReputation.sol and records the deployment.
 *
 * Usage:
 *   Local smoke test:   npx hardhat run scripts/deploy.cjs
 *   Polygon Amoy:       npx hardhat run scripts/deploy.cjs --network polygonAmoy
 *
 * Requires (in contracts/.env — see .env.example):
 *   PRIVATE_KEY           funded deployer key (TESTNET ONLY)
 *   POLYGON_AMOY_RPC_URL  optional RPC override
 *   POLYGONSCAN_API_KEY   optional, enables source verification after deploy
 */
const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const network = hre.network.name;
  const balance = await hre.ethers.provider.getBalance(deployer.address);

  console.log(`Network:   ${network} (chainId ${await hre.ethers.provider.getNetwork().then(n => n.chainId)})`);
  console.log(`Deployer:  ${deployer.address}`);
  console.log(`Balance:   ${hre.ethers.formatEther(balance)} POL`);
  console.log("");

  if (network !== "hardhat" && network !== "localhost" && balance === 0n) {
    throw new Error(
      "Deployer has no funds. Get testnet POL from https://faucet.polygon.technology/ and retry."
    );
  }

  const Reputation = await hre.ethers.getContractFactory("VouchReputation");
  const reputation = await Reputation.deploy();
  await reputation.waitForDeployment();

  const address = await reputation.getAddress();
  const tx = reputation.deploymentTransaction();

  console.log(`✅ VouchReputation deployed to: ${address}`);
  if (tx) console.log(`   Deploy tx:   ${tx.hash}`);

  // ── Record the deployment ──────────────────────────────
  const record = {
    contract: "VouchReputation",
    network,
    chainId: Number((await hre.ethers.provider.getNetwork()).chainId),
    address,
    deployer: deployer.address,
    deployTx: tx ? tx.hash : null,
    deployedAt: new Date().toISOString(),
  };
  const dir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${network}.json`);
  fs.writeFileSync(file, JSON.stringify(record, null, 2));
  console.log(`   Recorded:    ${file}`);

  // ── Optional source verification ───────────────────────
  if (process.env.POLYGONSCAN_API_KEY && network !== "hardhat" && network !== "localhost") {
    console.log("\nVerifying source on Polygonscan...");
    try {
      await hre.run("verify:verify", {
        address,
        constructorArguments: [],
      });
      console.log("✅ Verified on Polygonscan");
    } catch (e) {
      console.warn(`⚠️  Verification skipped/failed: ${e.message.split("\n")[0]}`);
    }
  }

  // ── Next steps for the operator ────────────────────────
  console.log("\nNext steps:");
  console.log(`  1. Add to backend/.env:`);
  console.log(`       REPUTATION_CONTRACT_ADDRESS=${address}`);
  console.log(`       PRIVATE_KEY=<the SAME funded key that deployed this contract>`);
  console.log(`     (the backend signer must equal the contract owner to anchor/attest)`);
  console.log(`  2. Restart the backend — POST /admin/run-phase3-jobs now goes on-chain.`);
  console.log(`  3. Sanity check: npx hardhat verify --network ${network} ${address}`);
}

main().catch((e) => {
  console.error("Deployment failed:", e?.message ?? e);
  process.exit(1);
});
