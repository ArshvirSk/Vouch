import { expect } from "chai";
import pkg from "hardhat";
const { ethers } = pkg;

describe("VouchReputation", function () {
  let Reputation, reputation, owner, other, subject;
  const SCORE = 8742n; // 87.42 * 100
  const NEG_SCORE = -1250n;

  beforeEach(async function () {
    [owner, other, subject] = await ethers.getSigners();
    Reputation = await ethers.getContractFactory("VouchReputation");
    reputation = await Reputation.deploy();
  });

  async function signAttestation(signer, user, score, observedAt) {
    // Must match the contract's abi.encode(user, score, observedAt) digest
    const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
      ["address", "int256", "uint256"],
      [user, score, observedAt]
    );
    const digest = ethers.keccak256(encoded);
    return signer.signMessage(ethers.getBytes(digest));
  }

  it("sets the right owner", async function () {
    expect(await reputation.owner()).to.equal(owner.address);
  });

  describe("reputation attestations", function () {
    it("stores a signed attestation and verifies it", async function () {
      const observedAt = 1700000000n;
      const sig = await signAttestation(owner, subject.address, SCORE, observedAt);

      await reputation.attestReputation(subject.address, SCORE, observedAt, sig);

      const [score, observed, , signature] = await reputation.getAttestation(subject.address);
      expect(score).to.equal(SCORE);
      expect(observed).to.equal(observedAt);
      expect(signature).to.equal(sig);
      expect(await reputation.verifyAttestation(subject.address)).to.be.true;
    });

    it("supports negative scores", async function () {
      const observedAt = 1700000000n;
      const sig = await signAttestation(owner, subject.address, NEG_SCORE, observedAt);
      await reputation.attestReputation(subject.address, NEG_SCORE, observedAt, sig);
      const [score] = await reputation.getAttestation(subject.address);
      expect(score).to.equal(NEG_SCORE);
      expect(await reputation.verifyAttestation(subject.address)).to.be.true;
    });

    it("rejects a tampered score", async function () {
      const observedAt = 1700000000n;
      // Signed for score 8742
      const sig = await signAttestation(owner, subject.address, SCORE, observedAt);
      // Attested with score 9999
      await expect(
        reputation.attestReputation(subject.address, 9999n, observedAt, sig)
      ).to.be.reverted;
    });

    it("rejects signatures from non-owner signers", async function () {
      const observedAt = 1700000000n;
      const forgedSig = await signAttestation(other, subject.address, SCORE, observedAt);
      await expect(
        reputation.attestReputation(subject.address, SCORE, observedAt, forgedSig)
      ).to.be.reverted;
    });

    it("rejects non-owner senders even with valid signature", async function () {
      const observedAt = 1700000000n;
      const sig = await signAttestation(owner, subject.address, SCORE, observedAt);
      await expect(
        reputation.connect(other).attestReputation(subject.address, SCORE, observedAt, sig)
      ).to.be.reverted;
    });

    it("emits ReputationAttested", async function () {
      const observedAt = 1700000000n;
      const sig = await signAttestation(owner, subject.address, SCORE, observedAt);
      await expect(reputation.attestReputation(subject.address, SCORE, observedAt, sig))
        .to.emit(reputation, "ReputationAttested")
        .withArgs(subject.address, SCORE, observedAt, (v) => true);
    });

    it("overwrites prior attestation with the latest score", async function () {
      const t1 = 1700000000n;
      const t2 = 1700001000n;
      const sig1 = await signAttestation(owner, subject.address, SCORE, t1);
      await reputation.attestReputation(subject.address, SCORE, t1, sig1);

      const NEW = 9100n;
      const sig2 = await signAttestation(owner, subject.address, NEW, t2);
      await reputation.attestReputation(subject.address, NEW, t2, sig2);

      const [score] = await reputation.getAttestation(subject.address);
      expect(score).to.equal(NEW);
    });
  });

  describe("batch anchoring + Merkle proofs", function () {
    it("anchors a root and verifies inclusion of a leaf", async function () {
      // 4-leaf balanced tree built the same way the backend builds roots:
      // nodes = keccak256(left ++ right)
      const leaves = [
        ethers.keccak256(ethers.toUtf8Bytes("commitment-1")),
        ethers.keccak256(ethers.toUtf8Bytes("commitment-2")),
        ethers.keccak256(ethers.toUtf8Bytes("commitment-3")),
        ethers.keccak256(ethers.toUtf8Bytes("commitment-4")),
      ];
      const h01 = ethers.keccak256(ethers.concat([leaves[0], leaves[1]]));
      const h23 = ethers.keccak256(ethers.concat([leaves[2], leaves[3]]));
      const root = ethers.keccak256(ethers.concat([h01, h23]));
      // Proof for leaves[0]: sibling leaves[1], then h23
      const proof = [leaves[1], h23];

      await reputation.anchorBatch(root);
      expect(await reputation.verifyRoot(root)).to.be.true;

      // Root already anchored
      await expect(reputation.anchorBatch(root)).to.be.reverted;

      // Inclusion proof verifies on-chain
      expect(await reputation.verifyInclusion(root, leaves[0], proof)).to.be.true;
      // A wrong leaf must not verify
      const wrong = ethers.keccak256(ethers.toUtf8Bytes("not-in-batch"));
      expect(await reputation.verifyInclusion(root, wrong, proof)).to.be.false;
    });

    it("rejects non-owner anchoring", async function () {
      const root = ethers.encodeBytes32String("root");
      await expect(reputation.connect(other).anchorBatch(root)).to.be.reverted;
    });
  });
});
