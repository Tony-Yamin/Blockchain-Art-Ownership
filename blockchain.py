import json
from typing import List

from block import Block, mine_block 
from transactions import Transaction


class BlockChain:
    def __init__(self):
        """
        Initialize the blockchain.
        """
        self.blocks: List[Block] = []    
        self.minted_artworks: set[str] = set()  


    def make_first_block(self, creator, recipient, artwork_id):
        """
        Create the very first block so the chain has a starting point.

        Args:
            creator (str): identifier who adds the first artwork
            recipient (str): identifier who receives the first artwork
            artwork_id (str): unique ID of the first artwork
        """
        if self.blocks:
            raise RuntimeError("First block already made!")

        add_transaction = Transaction(creator, recipient, artwork_id, "")
        add_transaction.sign(creator)         

        first = mine_block(0, "00" * 32, [add_transaction], 1, None, 0, 0)
        self.blocks.append(first)
        self.minted_artworks.add(artwork_id)


    def mine_next_block(self, tx_list):
        """
        Return a freshly mined block that builds on the current tip.
        
        Parameters:
            tx_list (list): list of transactions to include in the block

        Returns:
            Block: freshly mined block
        """
        if not self.blocks:
            raise RuntimeError("Make the first block before mining more.")

        parent_hash = self.blocks[-1].get_id()

        header_list = []
        for block in self.blocks:
            header_list.append(block.header)

        new_block = mine_block(len(self.blocks), parent_hash, tx_list, None, header_list, 10, 20000)
        return new_block


    def add_to_chain(self, block):
        """
        Validate basics then append to the chain if okay.
        
        Args:
            block (Block): block to add to the chain

        Returns:
            bool: True if the block was added, False otherwise
        """
        if block.header.prev_block_hash != self.blocks[-1].get_id():
            print("previous-hash mismatch — block rejected")
            return False
        if not block.validate():
            print("block.validate() failed — block rejected")
            return False
        
        for tx in block.transactions:
            if tx.sender == "MINT":
                if tx.artwork_id in self.minted_artworks:
                    print(f'duplicate MINT for "{tx.artwork_id}" — block rejected')
                    return False

        for tx in block.transactions:
            if tx.sender == "MINT":
                self.minted_artworks.add(tx.artwork_id)

        self.blocks.append(block)
        print("block added, height now", len(self.blocks) - 1)
        return True


    def show(self):
        """
        Print the blockchain.
        """
        for idx, blk in enumerate(self.blocks):
            print(f"{idx}: {blk.get_id()[:8]}…  txs={len(blk.transactions)}  diff={blk.header.difficulty}")

    
    def print_chain(self):
        """
        Print every block and its transactions, highlighting mint events.
        """
        for index, blk in enumerate(self.blocks):
            print(f"Block {index} - {blk.get_id()}")
            for tx in blk.transactions:
                if tx.sender == "MINT":
                    # special case: genesis or mint transaction
                    print(f" MINT: artwork '{tx.artwork_id}' to {tx.recipient}")
                else:
                    print(f" '{tx.sender}' to {tx.recipient}: artwork '{tx.artwork_id}'")
        
    def already_minted(self, artwork_id):
        """
        Check whether an an artwork_id was ever minted.
        
        Returns:
            True if we find a mint TX for this artwork, False otherwise.
        """
        for blk in self.blocks:
            for tx in blk.transactions:
                if tx.sender == "MINT" and tx.artwork_id == artwork_id:
                    return True
        return False
    
        
    def save(self, path: str):
        """
        Save the blockchain to a file.
        """
        with open(path, "w") as f:
            json.dump([b.to_dict() for b in self.blocks], f, indent=2)


    def load(self, path: str):
        """
        Load the blockchain from a file.
        """
        from block import load_block
        with open(path) as f:
            self.blocks = [load_block(obj) for obj in json.load(f)]



if __name__ == "__main__":
    chain = BlockChain()

    chain.make_first_block(creator="Alice", recipient="Gallery", artwork_id="MonaLisa")

    # create a sample transaction
    tx = Transaction("Alice", "Bob", "MonaLisa", "")
    tx.sign("Alice")

    # mine and add
    blk = chain.mine_next_block([tx])
    chain.add_to_chain(blk)

    chain.show()
