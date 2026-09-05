import { expect } from "chai";
import pkg from "hardhat";
const { ethers } = pkg;

describe("VouchAnchor", function () {
  let VouchAnchor, anchor, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    VouchAnchor = await ethers.getContractFactory("VouchAnchor");
    anchor = await VouchAnchor.deploy();
  });

  it("Should set the right owner", async function () {
    expect(await anchor.owner()).to.equal(owner.address);
  });

  it("Should anchor a batch and emit event", async function () {
    const mockRoot = ethers.encodeBytes32String("test_root");
    
    await expect(anchor.anchorBatch(mockRoot))
      .to.emit(anchor, "BatchAnchored")
      .withArgs(mockRoot, 1, (anyValue) => true);

    expect(await anchor.verifyRoot(mockRoot)).to.be.true;
    expect(await anchor.nextBatchId()).to.equal(2);
  });

  it("Should not allow non-owner to anchor", async function () {
    const mockRoot = ethers.encodeBytes32String("test_root");
    await expect(anchor.connect(addr1).anchorBatch(mockRoot))
      .to.be.revertedWith("Only owner can anchor");
  });

  it("Should not allow duplicate roots", async function () {
    const mockRoot = ethers.encodeBytes32String("test_root");
    await anchor.anchorBatch(mockRoot);
    
    await expect(anchor.anchorBatch(mockRoot))
      .to.be.revertedWith("Root already anchored");
  });
});
