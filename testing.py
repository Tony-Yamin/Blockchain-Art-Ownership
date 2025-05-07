
import threading
import time

from tracker import start_tracker
from peer import Peer
from blockchain import BlockChain
from transactions import Transaction
from block import calculate_merkle_root, adjust_difficulty, mine_block, BlockHeader

def start_tracker_thread(port=8000):
    """
    Launch the tracker in a background thread.
    """
    def run_tracker():
        start_tracker(port)
    t = threading.Thread(target=run_tracker, daemon=True)
    t.start()
    time.sleep(1)
    print("[Test1] Tracker started on port", port, "\n")


def test_p2p_network():
    """
    Test the P2P network.
    """
    print("Testing P2P Network")
    peer1 = Peer("127.0.0.1", 5001, "127.0.0.1", 8000)
    peer1.connect_to_tracker()
    print("[Test2] Peer1 peers list (expected []):", peer1.peers, "\n")

    peer2 = Peer("127.0.0.1", 5002, "127.0.0.1", 8000)
    peer2.connect_to_tracker()
    time.sleep(0.1)
    print("[Test3] After Peer2 joins:")
    print("Peer1 peers (expected [(127.0.0.1, 5002)]):", peer1.peers)
    print("Peer2 peers (expected [(127.0.0.1, 5001)]):", peer2.peers, "\n")

    peer3 = Peer("127.0.0.1", 5003, "127.0.0.1", 8000)
    peer3.connect_to_tracker()
    time.sleep(0.1)
    print("[Test4] After Peer3 joins:")
    print("Peer1 peers (expected two peers):", peer1.peers)
    print("Peer2 peers (expected two peers):", peer2.peers)
    print("Peer3 peers (expected two peers):", peer3.peers, "\n")

    peer3.close()
    time.sleep(0.1)
    print("[Test5] After Peer3 leaves:")
    print("Peer1 peers (should not include Peer3):", peer1.peers)
    print("Peer2 peers (should not include Peer3):", peer2.peers, "\n")

    peer1.close()
    peer2.close()
    
def test_block_broadcast():
    """
    Test the block broadcast between peers.
    """
    print("Testing Block Broadcast Between Peers")
    p1 = Peer("127.0.0.1", 5101, "127.0.0.1", 8000)
    p2 = Peer("127.0.0.1", 5102, "127.0.0.1", 8000)
    p1.connect_to_tracker()
    p2.connect_to_tracker()

    tx = Transaction("MINT", "Bob", "ART99", "")
    tx.sign("MINT")
    blk = p1.blockchain.mine_next_block([tx])
    p1.add_block(blk)     

    time.sleep(0.2) 

    print("Peer‑1 chain height:", len(p1.blockchain.blocks))
    print("[Test10] Peer‑2 chain height (should match):", len(p2.blockchain.blocks), "\n")

    p1.close() 
    p2.close()


def test_blockchain_basic():
    """
    Test the basic blockchain functionality.
    """
    print("Testing Basic Blockchain Functionality")
    bc = BlockChain()
    print("[Test6] Making genesis block:")
    bc.make_first_block("Alice", "Gallery", "ART1")
    print("Chain length (expected 1):", len(bc.blocks), "\n")

    print("[Test7] Mining and adding a transaction block:")
    tx = Transaction("Alice", "Bob", "ART1", "")
    tx.sign("Alice")
    blk = bc.mine_next_block([tx])
    added = bc.add_to_chain(blk)
    print("Block added (expected True):", added)
    print("Chain length (expected 2):", len(bc.blocks), "\n")

    print("[Test8] Invalid transaction signature detection:")
    bad_tx = Transaction("Alice", "Charlie", "ART1", "BADSIG")
    blk_bad = bc.mine_next_block([bad_tx])
    print("Block.validate() (expected False):", blk_bad.validate())
    print("Add invalid block (expected False):", bc.add_to_chain(blk_bad), "\n")

    print("[Test9] Duplicate mint rejection:")
    bc2 = BlockChain()
    bc2.make_first_block("MINT", "User1", "ARTX")
    mint_tx = Transaction("MINT", "User2", "ARTX", "")
    mint_tx.sign("MINT")
    blk_dup = bc2.mine_next_block([mint_tx])
    print("Add duplicate mint block (expected False):", bc2.add_to_chain(blk_dup), "\n")


def test_merkle_and_multiple_txs():
    """
    Test the merkle root and multiple transactions.
    """
    print("Testing Merkle Root and Multiple Transactions")
    tx1 = Transaction("S1", "R1", "ART2", "")
    tx1.sign("S1")
    tx2 = Transaction("S2", "R2", "ART3", "")
    tx2.sign("S2")
    merkle = calculate_merkle_root([tx1, tx2])
    print("Merkle root for 2 tx:", merkle)

    bc3 = BlockChain()
    bc3.make_first_block("MINT", "Owner", "GENART")
    hdrs = [b.header for b in bc3.blocks]
    blk_multi = mine_block(1, bc3.blocks[-1].get_id(), [tx1, tx2], None, hdrs, 1, 1)
    print("[Test11] Multi-tx block.validate() (expected True):", blk_multi.validate(), "\n")


def test_fork_resolution():
    """
    Test the fork resolution.
    """
    print("Testing Fork Resolution")
    peer_temp = Peer("127.0.0.1", 6001, "127.0.0.1", 8000)
    peer_temp.blockchain = BlockChain()
    peer_temp.blockchain.make_first_block("MINT", peer_temp.ip, "GEN")
    peer_temp.all_blocks = {b.get_id(): b for b in peer_temp.blockchain.blocks}

    txa = Transaction("MINT", "A", "AID", "")
    txa.sign("MINT")
    blockA = mine_block(1, peer_temp.blockchain.blocks[-1].get_id(), [txa], None, [peer_temp.blockchain.blocks[0].header], 1, 1)
    txb = Transaction("MINT", "B", "BID", "")
    txb.sign("MINT")
    blockB = mine_block(1, peer_temp.blockchain.blocks[-1].get_id(), [txb], None, [peer_temp.blockchain.blocks[0].header], 1, 1)
    peer_temp.all_blocks[blockA.get_id()] = blockA
    peer_temp.all_blocks[blockB.get_id()] = blockB

    txa2 = Transaction("A", "A2", "AID2", "")
    txa2.sign("A")
    blockA2 = mine_block(2, blockA.get_id(), [txa2], None, [peer_temp.blockchain.blocks[0].header, blockA.header], 1, 1)
    peer_temp.all_blocks[blockA2.get_id()] = blockA2

    best_chain = peer_temp.find_longest_chain()
    print("[Test12] Longest chain length (expected 3):", len(best_chain), "\n")


def test_dynamic_difficulty():
    """
    Test the dynamic difficulty adjustment.
    """
    print("Testing Dynamic Difficulty Adjustment")
    now_ms = int(time.time() * 1000)
    headers = [BlockHeader(i, "00"*32, "00"*32, now_ms + i*10000, 3, 0) for i in range(3)]
    new_diff = adjust_difficulty(headers, window=2, target_time=5)
    print("[Test13] New difficulty (bits):", new_diff, "\n")


def test_resilience_to_tampering():
    """
    Test the resilience of the blockchain to tampering.
    """
    print("Testing Resilience to Tampering")
    bc4 = BlockChain()
    bc4.make_first_block("MINT", "U", "ART123")
    txc = Transaction("MINT", "U", "ARTX", "")
    txc.sign("MINT")
    block_orig = bc4.mine_next_block([txc])

    tampered = block_orig
    tampered.header.prev_block_hash = "ff"*32
    
    print("[Test15] Add tampered block (expected False):", bc4.add_to_chain(tampered), "\n")



if __name__ == "__main__":
    start_tracker_thread()
    test_p2p_network()
    test_blockchain_basic()
    test_block_broadcast()
    test_merkle_and_multiple_txs()
    test_fork_resolution()
    test_dynamic_difficulty()
    test_resilience_to_tampering()
