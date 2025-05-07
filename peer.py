import socket
from blockchain import BlockChain
import json
from transactions import Transaction
from block import load_block
import time
import threading
import os

class Peer:
    def __init__(self, ip, port, tracker_ip, tracker_port):
        self.ip = ip
        self.port = port
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.alive_bool = False
        
        # #mining loop control
        # self.mining_bool = False
        
        # self.stop_event = threading.Event()

        self.blockchain = BlockChain() # our private ledger
        
        self.pending_transactions = [] # unconfirmed Transaction objects
        self.unseen_blocks = {} # blocks whose parent we havent seen befor
        self.peers = [] # [(ip, port), …] addresses of other peers
        
        self.all_blocks = {} # keeping every block we have seen
        
        self.chain_file = "chain.json" # where we'll save/load the chain
        
        self.load_create_chain() # load or create the genesis chain
        
    def load_create_chain(self):
        """
        Load the chain from disk if it exists, otherwise make the genesis block.
        """
        if os.path.exists(self.chain_file):
            # load all the blocks from JSON on disk
            self.blockchain.load(self.chain_file)
        else:
            # create a first block
            self.blockchain.make_first_block(creator="MINT",
                                             recipient=self.ip,
                                             artwork_id="GENESIS_ART")
        for blk in self.blockchain.blocks:
            self.all_blocks[blk.get_id()] = blk
                
        
    def connect_to_tracker(self):

        message = {
            "message_type": "JOIN",
            "ip": self.ip,
            "port": self.port
        }
        
        # open, send, recv, then close     
        with socket.create_connection((self.tracker_ip, self.tracker_port), timeout=5) as s:
            #print("[DEBUG][peer] Connected to tracker", flush=True)
            s.sendall((json.dumps(message) + "\n").encode())
            #print("[DEBUG][peer] JOIN sent", flush=True)
            time.sleep(0.05)
            raw = s.recv(2048).decode().strip()
            #print(f"[DEBUG][peer] raw reply: {raw}", flush=True)

            message = json.loads(raw)
            if message.get("message_type") == "PEER_LIST":
                for peer in message.get("peers", []):
                    if ((peer["ip"], peer["port"]) != (self.ip, self.port)) and ((peer["ip"], peer["port"]) not in self.peers):
                        self.peers.append((peer["ip"], peer["port"]))
            else:
                print(f"[ERROR][peer] unexpected reply: {message}", flush=True)
        
        self.listen_thread = threading.Thread(target=self.receive_message, daemon=True)
        self.listen_thread.start()
        
        if not self.alive_bool:
            # keep-alive thread
            self.alive_thread = threading.Thread(target=self.keep_alive, daemon=True)
            self.alive_thread.start()
            self.alive_bool = True
        
        # if not self.mining_bool:
        #     # mining thread
        #     self.mining_thread = threading.Thread(target=self.mine_loop(), daemon=True)
        #     self.mining_thread.start()
        #     self.mining_bool = True
        

    def add_block(self, block):
        """
        Add a block to the blockchain.

        Args:
            block (Block): The block to add to the blockchain.
        """
        self.blockchain.add_to_chain(block)

        message = {
            "message_type": "NEW_BLOCK", 
            "data": block.to_dict()
        }

        for (peer_ip, peer_port) in self.peers:
            if peer_ip == self.ip and peer_port == self.port:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((peer_ip, peer_port))
                sock.sendall((json.dumps(message) + "\n").encode())
                sock.close()
            except:
                pass
            
    def broadcast_transaction(self, tx):
        """
        Send a NEW_TRANSACTION message to every peer in self.peers.

        Args:
            tx (Transaction): The transaction to broadcast.
        """
        
        message = {
            "message_type": "NEW_TRANSACTION",
            "data": tx.to_dict()
        }
        
        for (peer_ip, peer_port) in self.peers:
            try:
                with socket.create_connection((peer_ip, peer_port), timeout=3) as s:
                    s.sendall((json.dumps(message) + "\n").encode())
            except Exception:
                # if send fails, remove stale peers
                self.peers.remove((peer_ip, peer_port))
                pass
            
    def submit_transaction(self, sender, recipient, artwork_id, sender_key):
        """
        Create, sign, store, and broadcast a new transaction.
        
        Args:
            sender_key (str): HMAC key to sign with, so the private key. 
        """
        
        tx = Transaction(sender, recipient, artwork_id, signature="")
        # sign it in-place using the sender_key
        tx.sign(sender_key)
        self.pending_transactions.append(tx)
        # broadcast it to all peers
        self.broadcast_transaction(tx)
        
    
    def keep_alive(self):
        """
        Keep the peer alive by sending keep-alive messages to the tracker.
        """
        while True:
            if self.stop_event.is_set():
                break

            message = {
                "message_type": "KEEP_ALIVE",
                "ip": self.ip,
                "port": self.port
            }
            with socket.create_connection((self.tracker_ip, self.tracker_port), timeout=3) as s:
                s.sendall((json.dumps(message) + "\n").encode())
            
            self.stop_event.wait(10)


    def receive_message(self):
        """
        Receive messages from other peers.
        """
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.ip, self.port))
        listener.listen()
        listener.settimeout(1)

        self.pending_transactions = []
        while True:
            if self.stop_event.is_set():
                break
            try:
                connection, address = listener.accept()
            except socket.timeout:
                continue
            #connection, address = listener.accept()
            response = connection.recv(4096).decode().strip()
            connection.close()

            message = json.loads(response)
            message_type = message["message_type"]

            if message_type == "NEW_TRANSACTION":
                data = message.get("data", [])
                transaction = Transaction.from_dict(data)
                if transaction.verify_signature():
                    self.pending_transactions.append(transaction)

            if message_type == "NEW_BLOCK":
                block_dict = message.get("data", [])
                block = load_block(block_dict)
                
                ### for forking
                block_id = block.get_id()
                self.all_blocks[block_id] = block
                
                # trying to append it diretcly to current tip
                tip_hash = self.blockchain.blocks[-1].get_id()
                if block.header.prev_block_hash == tip_hash:
                    if self.blockchain.add_to_chain(block):
                        confirmed_transactions = []
                        for transaction in block.transactions:
                            confirmed_transactions.append(transaction)
                            self.pending_transactions = []
                            for pending_transaction in self.pending_transactions:
                                if pending_transaction not in confirmed_transactions:
                                    self.pending_transactions.append(pending_transaction)
                
                # recomputing the longest valid chain from all_blocks
                best_chain = self.find_longest_chain()
                if len(best_chain) > len(self.blockchain.blocks):
                    #swap in longer chain
                    self.blockchain.blocks = best_chain
                    
                    # buliding a set of all transactions in the chosen best_chain
                    all_transactions = set()
                    for b in best_chain:
                        for tx in b.transactions:
                            all_transactions.add(tx)
                            
                    # rebuilding pending_transactions list to include only transactions not yet included in any block of best_chain
                    new_pending = []
                    for tx in self.pending_transactions:
                        if tx not in all_transactions:
                            new_pending.append(tx)
                    
                    # replacing with the updatd list
                    self.pending_transactions = new_pending
            
            if message_type == "PEER_UPDATE":
                peers = message.get("peers", [])
                self.peers = []
                for peer in peers:
                    if (peer["ip"], peer["port"]) != (self.ip, self.port):
                        self.peers.append((peer["ip"], peer["port"]))

    
    def find_longest_chain(self):
        """
        Find the longest chain in the blockchain.
        """
        zero_hash = "00" * 32
        best = []
        
        for blk in self.all_blocks.values():
            chain = []
            current = blk
            
            # walk backward until we hit genesis or a gap
            while True:
                chain.append(current)
                previous = current.header.prev_block_hash
                if previous == zero_hash:
                    break # reached genesis
                if previous in self.all_blocks:
                    current = self.all_blocks[previous]
                else:
                    # discard this chain]
                    chain = []
                    break
                
            if chain and len(chain) > len(best):
                chain.reverse()
                best = chain
                
        return best
    
    
    def close(self):
        """
        Close the peer.
        """
        # stop threads
        self.stop_event.set()
        
        leave_message = {
            "message_type": "LEAVE",
            "ip": self.ip,
            "port": self.port
        }
        
        # sending LEAVE 
        try:
            with socket.create_connection((self.tracker_ip, self.tracker_port), timeout=3) as s:
                s.sendall((json.dumps(leave_message) + "\n").encode())
            self.listen_thread.join()
            self.alive_thread.join()
        except Exception:
            pass
        



        





        
        
