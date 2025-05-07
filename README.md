

Project Overview
----------------
BrushChain Collective is a fully decentralised blockchain written in Python that registers the ownership and transfer of artworks. A single tracker server helps peers discover one another, but every block, transaction, and consensus decision is handled at the edge: each peer keeps its own complete copy of the chain, mines proof‑of‑work blocks, verifies incoming data, and resolves forks by picking the longest valid branch. Blocks contain Merkle‑rooted lists of signed transactions, enabling many transfers per block while retaining quick, verifiable proofs. A dynamic mining difficulty is adjusted every ten blocks toward a 20‑second target. Together, the modules (transactions.py, block.py, blockchain.py, peer.py, and tracker.py) form a complete blockchain and P2P network that demonstrates peer discovery, secure transaction handling, and adaptive PoW.

transactions.py 
---------------
This class defines a Transaction record plus helper functions to sign, verify, and (de)serialise artwork‑transfer messages.

block.py
--------
This class implements the low‑level block functionalities: BlockHeader, Block, Merkle‑tree construction, and the proof‑of‑work mining loop.

blockchain.py
-------------
This class implements the BlockChain, along with methods to mine a block, create a block, and adjust the difficulty of mining a block based on the networks conditions.

peer.py
-------
This class implements a node in the peer-to-peer network. Each peer loads its local chain, connects to the tracker, and broadcasts transactions and blocks, while handling forking.

tracker.py
----------
This class implements the tracker of a peer-to-peer network. The tracker keeps a list of all of the active peers and broadcasts any updates made to the active peers list in the network to let ny peer know of the other peers. 

Together these files create a self‑contained, decentralised network where peers discover each other through the tracker, exchange signed transactions, mine new blocks, and agree on a single canonical chain.

Instructions to run our code
----------------------------
For example, if we wanted to run a P2P network with 1 tracker and 3 peers, these are the steps to follow:
1. run the following command to start the tracker: python3 tracker.py <tracker_port>
2. run the following command for the 1st peer: python3 peer.py <peer1_ip> <peer1_port> <tracker_ip> <tracker_port>
3. run the following command for the 2nd peer: python3 peer.py <peer2_ip> <peer2_port> <tracker_ip> <tracker_port>
4. run the following command for the 3rd peer: python3 peer.py <peer3_ip> <peer3_port> <tracker_ip> <tracker_port>

This chain of commands sets up the P2P network between the tracker and the 3 peers. Furthermore, each peer sends a keep_alive message to the tracker to indicate an active status every 10 seconds. In order to implement the blockchain and mining blocks, we wrote a testing.py file which we also provide along with our submission to showcase hoe to use the functions we defined in the Peer class. The outputs verifying the functionality of the project along with an explanation of the results can be found in the TESTING.md file. Furthermore, in order to run the UI design, we provided the run_network.py file to make it simpler. 
RUN: ***python testing.py***


UI Demo
-----------------------------------
The UI consists of displaying our blockchain applicarion. It lists the blocks on the blockchain and allows to add and mine block. Each peer has their own instance of the UI (running on a different port), and adding a block on any peer is displayed on all.

ui.py
----------
A Flask file that wraps each `peer.py` instance with a modern HTML/JS interface to fetch blockchain and peer information.

app.js 
----------
JS file for the UI's blockchain's block displayers, animate new blocks, and show friendly error messages (shake + slide‑in) when someone tries to cheat.  

index.html
----------
The main html page to render the UI.

run_network.py
---------------
File to run UI so the entire network (tracker + N peers + N UIs) starts with a single command

Instructions to run 
--------------------
***python run_network.py***