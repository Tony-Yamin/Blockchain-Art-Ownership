Overview of the Application Design
----------------------------------
BrushChain Collective is a peer‑to‑peer blockchain that records the registry of digital or physical artworks. Every peer keeps a full copy of the blockchain, mines new proof‑of‑work blocks, and broadcasts blocks and transactions to the other peers in the network. A tracker exists in the peer-to-peer network to keep track of the active peers and let each peer know about the other peers in the network.

transactions.py
---------------
This file defines the Transaction class. 
A transaction stores four main components:
- sender: the current owner (or the word MINT for the very first issue).
- recipient: who should own the piece after this transaction is accepted.
- artwork_id: a unique label for the artwork.
- signature: a 64‑character hexadecimal string that acts as a stamp of authenticity.

Functions:
- sign(secret) builds the message sender|recipient|artwork_id and runs it through HMAC‑SHA‑256 with the owner’s secret key. 
- verify() runs the same calculation again and compares the two results using hmac.compare_digest. That helper always takes the same amount of time, so any timing attack is immediately stopped.
- to_dict() and from_dict() convert between the Python object and a dictionary, creating a universal message format for broadcasting transactions between peers.
It is important to note that we used Python's built-in hashlib to compute the hash of blocks and transactions.
The class is declared frozen=True, which makes every field read‑only after construction. That lets different threads share the same transaction safely and lets us store transactions in sets without extra copying. If a peer receives a transaction whose signature is wrong, it simply drops the message and keeps the connection open.

block.py
--------
This file defines the BlockHeader and Block classes, the core pieces of the blockchain.
BlockHeader fields:
- block_num: the height of the block.
- prev_block_hash: SHA‑256 hash of the previous block header.
- merkle_root_hash: root hash that secures all transactions in the block.
- timestamp_ms: current Unix time in milliseconds.
- difficulty: number of leading zero bits the block’s hash must show.
- nonce: 64‑bit value miners change until the hash meets the target.

Block fields:
- header: the BlockHeader described above.
- transactions: block transactions.

Functions:
- calculate_merkle_root(txs) pairs up transaction hashes, hashes them, and repeats until one hash is left; if there is an odd count, the final hash is copied so the tree stays balanced. (BONUS)
- mine_block(prev_header, txs, target_difficulty) tries nonce values one by one until the double‑SHA‑256 of the header shows the required number of leading zeros. (implemented as instructed in the class powerpoint and suggested video)
- validate(prev_header) re‑checks linkage, proof‑of‑work, Merkle root, and every transaction signature before a block can be accepted.
Because every block carries its own Merkle root we can pack many transactions inside and still verify each one quickly, therefore correctly implementing the Merkle Tree bonus feature.

blockchain.py
-------------
This file implements the Blockchain class.
Main data structures:
- blocks: a list with the current main blockchain.
- minted_artworks: a set that records which artwork IDs have already been minted, so no one can mint the same piece twice.

Functions:
- make_first_block() builds the genesis block with a single MINT transaction.
- add_to_chain(block) checks previous‑hash link, proof‑of‑work, Merkle root, each transaction signature, duplicate‑mint rule, and correct height before appending.
- mine_next_block() grabs up to 512 pending transactions, calls adjust_difficulty() to implement a dynamic adjustment of the mining difficulty, and then mines a new block.
- adjust_difficulty() looks at the last 10 blocks and raises or lowers the target by one bit so average solve time stays close to 20 seconds. (BONUS)
- save() and load() write and read the whole chain to chain.json, which we used for debugging purposes.

peer.py
-------
This module implements the Peer class, which represents a node in the P2P network.
Key components:
- sockTCP listening socket.
- peers: list of (ip, port) tuples received from the tracker.
- pending_transactions: a list of transactions waiting to be added to the blockchain.
- all_blocks: dictionary of every block the peer has heard about, used for fork handling.
- blockchain: the current main blockchain.
- lock and stop_event: keep shared data safe and support clean shutdown.

Threads launched and functions: to ensure that all of the required functionalities were implemented, we used multithreading in our Peer class
- listener thread: accepts connections, reads one JSON line per packet, and dispatches
- keep alive thread: sends KEEP_ALIVE to the tracker every 10 seconds, pulse messages (method verified on EdDiscussion by the professor).

Fork handling:
In order to handle forking, we chose to implement the longest chain as the decision factor.

tracker.py
----------
The tracker is a very small server that only helps peers find each other: it never touches blockchain data.
State kept:
- peers_last_seen: dictionary mapping (ip, port) to the last time the peer pinged, to keep track of the active peers in the network.

Messages handled:
- JOIN: add the peer to the table and send back a full PEER_LIST.
- KEEP_ALIVE: update last_seen time; no reply needed.
- LEAVE: remove the peer right away.

Whenever a peer enters or leaves the network, the tracker broadcasts PEER_UPDATE so every node has the same list.
A janitor loop runs every five seconds and removes any peer that has not sent a keep_alive message in 40 seconds, which is the time limit we chose.

UI Design
---------
We built a UI that displays the blockchain and its funcrionslity live and in real time.Each peer runs a lightweight Flask adapter (`ui.py`) -- running on its own port -- that serves a one‑page web interface. Adding a block will be directly displayed on each of the peer's blockchains (i.e web pages) without needing to refresh.

- templates/index.html 
This is the single web page that users open in their browser. It lays out the “Mine a Block” form on the left and the growing list of blocks on the right. It also reserves spots for the project logo in the top corner and a badge showing which peer you’re connected to.

- static/style.css
This file defines the look and feel of the page: soft cream background, warm accent color for buttons and highlights, and gentle animations for new blocks and error feedback. It also sizes and positions the logo and peer-number badge so the interface feels balanced and inviting.

- static/app.js
This script brings the page to life. When you load it, it asks the server for the current chain and displays it. It then listens quietly in the background for new blocks so you never have to refresh. When you press “Mine & Broadcast,” it sends your data to the server and shows a friendly shake if something goes wrong.

- ui.py
Each peer runs this small Python web server alongside the main blockchain code. It serves the HTML, CSS and JavaScript files, handles requests to add or receive blocks, and makes sure every browser window stays in sync. A tiny file-watcher notices when the shared `chain.json` file changes and quietly pushes the updated list of blocks to your page.

Bonus Features Implemented
--------------------------
1. UI: The UI is a single-page web interface with a left-hand form for mining new blocks and a right-hand, scrollable timeline of block cards showing the entire chain. Each peer has an instance of the webpage. It updates in real time—new blocks gently fade in and errors trigger a quick shake—so you never have to reload the page. A small peer badge and logo in the header keep the look clean, friendly, and instantly recognizable.

2. Dynamic difficulty adjustment: to keep block times steady even when the total mining power goes up or down, the code automatically adusts the difficulty based on the computing power of the network. Every time ten new blocks have been added, we measure how long those ten took to solve. If they arrived too fast (under about 180 seconds total) we raise the difficulty by one leading‑zero bit; if they were too slow (over about 220 seconds) we lower it by one bit. The new difficulty is written into the next block header, so all miners immediately start working at the updated target.

3. Merkle Tree: each block can now hold a whole list of transactions instead of just one. Before a block is mined we hash every transaction, then keep hashing pairs of hashes upward until only one value, the Merkle root, remains. That root is stored in the block header. When a peer later wants to prove a single transfer is inside the block, it just sends that transfer plus the few hashes needed to rebuild the path to the root. The verifier rebuilds the path and checks that the result matches the root in the header; if it does, the transaction is confirmed.

4. Logo: we designed a logo for our project! We submitted a picture of it and included it in the UI.
