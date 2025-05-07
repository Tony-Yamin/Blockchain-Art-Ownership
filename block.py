import time
import struct
import hashlib
import math
from typing import List
from transactions import Transaction


def hash_data(data):
    """
    Return the SHA-256 hash of data as a hex string.

    Parameters:
        data (bytes): input data to hash
    Returns:
        str: 64-character hex digest
    """
    return hashlib.sha256(data).hexdigest()


def calculate_merkle_root(transactions):
    """
    Compute the Merkle root from a list of transactions.

    If there's an odd number of hashes, duplicate the last one.

    Parameters:
        transactions (List[Transaction]): list of transaction objects
    Returns:
        str: hex string of the Merkle root
    """
    if not transactions:
        return hash_data(b"") 

    # Start with each tx's hash as bytes
    current = []
    for transaction in transactions:
        current.append(bytes.fromhex(transaction.hash()))

    while len(current) > 1:
        if len(current) % 2 == 1:
            current.append(current[-1])

        new_level = []
        for i in range(0, len(current), 2):
            new_hash = hash_data(current[i] + current[i+1])
            new_level.append(bytes.fromhex(new_hash))
        current = new_level

    return current[0].hex()


class BlockHeader:
    """
    Metadata for a block, including proof-of-work details.
    """
    def __init__(self, block_num, prev_block_hash, merkle_root_hash, timestamp_ms, difficulty, nonce):
        """
        Initialize the block header.
        """
        self.block_num = block_num
        self.prev_block_hash = prev_block_hash
        self.merkle_root_hash = merkle_root_hash
        self.timestamp_ms = timestamp_ms
        self.difficulty = difficulty
        self.nonce = nonce

    def to_bytes(self):
        """
        Serialize header fields to bytes for hashing.

        Returns:
            bytes: concatenated header bytes
        """
        num_bytes = struct.pack(">I", self.block_num)
        prev_bytes = bytes.fromhex(self.prev_block_hash)
        merkle_bytes = bytes.fromhex(self.merkle_root_hash)
        time_bytes = struct.pack(">Q", self.timestamp_ms)
        bits_bytes = struct.pack(">I", self.difficulty)
        nonce_bytes = struct.pack(">I", self.nonce)
        return num_bytes + prev_bytes + merkle_bytes + time_bytes + bits_bytes + nonce_bytes

    def hash_header(self):
        """
        Compute SHA-256 hash of the header bytes.

        Returns:
            str: hex digest
        """
        return hash_data(self.to_bytes())

    def __repr__(self):
        """
        Return a string representation of the block header.

        Returns:
            str: string representation of the block header
        """
        return (f"BlockHeader(num={self.block_num}, prev={self.prev_block_hash[:8]}..., "
                f"merkle={self.merkle_root_hash[:8]}..., bits={self.difficulty}, nonce={self.nonce})")


class Block:
    """
    A blockchain block containing a header and transactions.
    """
    def __init__(self, header, transactions):
        """
        Initialize the block.
        """
        self.header = header
        self.transactions = transactions


    def get_id(self):
        """
        Get the block's unique ID (its header hash).

        Returns:
            str: hex hash string
        """
        return self.header.hash_header()


    def to_dict(self):
        """
        Convert block to dictionary for JSON serialization.

        Returns:
            dict: with 'header' and 'transactions'
        """
        return {
            "header": {
                "block_num": self.header.block_num,
                "prev_block_hash": self.header.prev_block_hash,
                "merkle_root_hash": self.header.merkle_root_hash,
                "timestamp_ms": self.header.timestamp_ms,
                "difficulty": self.header.difficulty,
                "nonce": self.header.nonce
            },
            "transactions": [tx.to_dict() for tx in self.transactions]
        }


    def validate(self):
        """
        Check Merkle root, proof-of-work, and transaction signatures.

        Returns:
            bool: True if valid, False otherwise
        """
        # Merkle check
        if self.header.merkle_root_hash != calculate_merkle_root(self.transactions):
            return False

        # Proof-of-work check
        if int(self.get_id(), 16) > (1 << (256 - self.header.difficulty)) - 1:
            return False

        # Transaction signature check
        for tx in self.transactions:
            if not tx.verify_signature():
                return False

        return True



def adjust_difficulty(recent_headers, window, target_time):
    """
    Dynamically adjust difficulty based on the last `window` blocks.

    Args:
        recent_headers: list of headers in chain order (oldest→newest)
        window: how many blocks to look back
        target_time: desired seconds per block

    Returns:
        int: new difficulty (in bits)
    """
    if len(recent_headers) < window + 1:
        if recent_headers:
            return recent_headers[-1].difficulty 
        else:
            return 1

    old_header = recent_headers[-(window + 1)]
    new_header = recent_headers[-1]
    actual_time = (new_header.timestamp_ms - old_header.timestamp_ms) / 1000.0
    expected = window * target_time
    ratio = max(0.25, min(actual_time / expected, 4.0))
    last_bits = new_header.difficulty
    new_bits = last_bits + round(math.log2(ratio))
    return max(1, new_bits)



def mine_block(block_number, prev_hash, transactions, difficulty, chain_headers, window, target_time):
    """
    Create and mine a block, auto‐adjusting difficulty if chain_headers is given.

    Parameters:
        block_number: the height of this block
        prev_hash: hex hash of previous block
        transactions: list of Transaction objects
        difficulty: fixed difficulty (if you don’t want auto‐adjust)
        chain_headers: full chain of BlockHeader to compute new difficulty
        window: how many blocks to look back (for auto‐adjust)
        target_time: desired seconds per block (for auto‐adjust)

    Returns:
        Block: newly mined block
    """
    if difficulty is None and chain_headers is not None:
        difficulty = adjust_difficulty(chain_headers, window, target_time)
    elif difficulty is None:
        difficulty = 1

    merkle_root = calculate_merkle_root(transactions)
    timestamp_ms = int(time.time() * 1000)
    header = BlockHeader(block_number, prev_hash, merkle_root, timestamp_ms, difficulty, nonce=0)

    while int(header.hash_header(), 16) > (1 << (256 - difficulty)) - 1:
        header.nonce += 1

    return Block(header, transactions)



def load_block(data):
    """
    Reconstruct a Block from its dictionary form.

    Args:
        data: dict output by Block.to_dict()
    Returns:
        Block: rebuilt block object
    """
    data_header = data["header"]
    header = BlockHeader(data_header["block_num"], data_header["prev_block_hash"], data_header["merkle_root_hash"],
    data_header["timestamp_ms"], data_header["difficulty"], data_header["nonce"])

    transactions = []
    for transaction in data.get("transactions", []):
        transactions.append(Transaction.from_dict(transaction))

    return Block(header, transactions)
