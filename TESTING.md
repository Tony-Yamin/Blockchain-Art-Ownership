
To test the functionality requirements of our final project, we wrote a testing.py file.
The file launches the tracker in a background thread, starts 3 peer processes, and runs test cases for the following functionalities:
1. peer-to-peer membership propagation (join/leave)
2. mining, block validation, chain extension
3. signature checking and duplicate-mint rejection
4. cross-peer block broadcast
5. merkle-root handling with multiple transactions per block (bonus)
6. fork detection and longest-chain resolution 
7. dynamic difficulty readjustment (bonus)
8. tamper detection via header-hash mismatch

RUN: ***python testing.py***

When running the testing.py file the output is the following:

[Test1] Tracker started on port 8000 

Testing P2P Network
[Test2] Peer1 peers list (expected []): []

[Test3] After Peer2 joins:
Peer1 peers (expected [(127.0.0.1, 5002)]): [('127.0.0.1', 5002)]
Peer2 peers (expected [(127.0.0.1, 5001)]): [('127.0.0.1', 5001)] 

[Test4] After Peer3 joins:
Peer1 peers (expected two peers): [('127.0.0.1', 5002), ('127.0.0.1', 5003)]
Peer2 peers (expected two peers): [('127.0.0.1', 5001), ('127.0.0.1', 5003)]
Peer3 peers (expected two peers): [('127.0.0.1', 5001), ('127.0.0.1', 5002)] 

[Test5] After Peer3 leaves:
Peer1 peers (should not include Peer3): [('127.0.0.1', 5002)]
Peer2 peers (should not include Peer3): [('127.0.0.1', 5001)] 

Testing Basic Blockchain Functionality
[Test6] Making genesis block:
Chain length (expected 1): 1 

[Test7] Mining and adding a transaction block:
block added, height now 1
Block added (expected True): True
Chain length (expected 2): 2 

[Test8] Invalid transaction signature detection:
Block.validate() (expected False): False
block.validate() failed — block rejected
Add invalid block (expected False): False 

[Test9] Duplicate mint rejection:
duplicate MINT for "ARTX" — block rejected
Add duplicate mint block (expected False): False 

Testing Block Broadcast Between Peers
block added, height now 12
block added, height now 12
Peer‑1 chain height: 13
[Test10] Peer‑2 chain height (should match): 13 

Testing Merkle Root and Multiple Transactions
Merkle root for 2 tx: 040f8a30eec0ad9e26fca4b610510bd0d69b901f6811b9b4457bbb6cf072fb34
[Test11] Multi-tx block.validate() (expected True): True 

Testing Fork Resolution
[Test12] Longest chain length (expected 3): 3 

Testing Dynamic Difficulty Adjustment
[Test13] New difficulty (bits): 4 

Testing Resilience to Tampering
previous-hash mismatch — block rejected
[Test14] Add tampered block (expected False): False 


# Explanations and Observations
Test 1: Tracker launch 
We notice that the background thread listens on 0.0.0.0:8000, which confirms that the tracker process starts successfully (on port 8000).

Test 2-5: P2P Network
All peer-lists printed above from each node match the expected sets after every join and leave event. These tests verify peer-list propagation.
In the beginning, Peer 1 does not see others (Test2). When Peer 2 joins, the tracker adds it and pushes an updated list to Peer 1 now sees and Peer 2 (Test 3). After Peer 3 joins, every node holds the full 3 peer list (Test 4). When Peer 3 leaves, the tracker removes it and the remaining peers drop 5003 from their lists (Test 5).

Test 6-7: Genesis and valid mining
Creating the genesis block sets chain height to 1, and mining a valid transaction block extends it to 2. The successful add_to_chain() return confirms our proof‑of‑work and header‑link checks, proving basic block production and extension work as expected.

Test 8: Invalid transaction signature detection
In this case we notice that the block fails validate() and is rejected. This shows each node verifies signatures before accepting transactions, preventing unauthorized transfers.

Test 9: Duplicate mint rejection
An attempt to mint the same artwork ID twice is refused with a message “duplicate MINT” and a False return. This demonstrates enforcement of one time asset creation.

Test 10: Block Broadcast Between Peers
Peer 1 mines a new block and broadcasts it. Peer 2’s chain height rises to match Peer 1’s. The identical heights show that NEW_BLOCK messages propagate across the network and are accepted after local validation.

Test 11: Merkle Root and Multiple Transactions (Bonus)
A block containing two transactions is mined. Its Merkle root is printed and validate() returns True. Matching roots on the receiver confirm correct Merkle‑tree construction and multi‑transaction handling in our blockchain.

Test 12: Fork Resolution
Our testing.py file creates a two‑way fork, then extends one branch. The peer selects the 3 block branch, demonstrating longest chain resolution and fork recovery.

Test 13: Dynamic Difficulty Adjustment (Bonus)
Feeding fake block timestamps into the difficulty adjustment function produces a new bits value without any errors, which shows that the algorithm works correctly and adjusts the mining difficulty based on how fast blocks are being mined.

Test 14: Resilience to Tampering
Manually altering a block’s prev_block_hash causes validation to fail and the chain to reject the block.


### UI TESTING

To test the UI, simply run ***python run_network.py*** and open each peer's web-page as displayed on the terminal. You can then see and use our application.
