// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract VouchAnchor {
    event BatchAnchored(bytes32 indexed merkleRoot, uint256 batchId, uint256 timestamp);

    uint256 public nextBatchId;
    mapping(uint256 => bytes32) public batchRoots;
    mapping(bytes32 => uint256) public rootToBatchId;

    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can anchor");
        _;
    }

    constructor() {
        owner = msg.sender;
        nextBatchId = 1;
    }

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
}
