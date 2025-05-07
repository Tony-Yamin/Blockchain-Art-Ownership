import argparse, json, os, queue, threading, time, requests
from flask import Flask, request, jsonify, Response, render_template
from blockchain   import Block
from transactions import Transaction

import peer
try:
    blockchain = peer.blockchain
except AttributeError:
    from blockchain import BlockChain
    blockchain = BlockChain()
    try:
        blockchain.load("chain.json")
    except FileNotFoundError:
        blockchain.make_first_block("MINT", "SERVER", "GENESIS_ART")
        blockchain.save("chain.json")
    peer.blockchain = blockchain


app = Flask(__name__, template_folder="templates", static_folder="static")
subscribers: set[queue.Queue] = set()

TRACKER_URL = ""
PEER_PORT   = 0
PEER_ADDR   = ""
UI_PORT     = 0
peer_list   = []

CHAIN_FILE  = "chain.json"
_chain_mtime = os.path.getmtime(CHAIN_FILE) if os.path.exists(CHAIN_FILE) else 0

def sync_chain():
    """
    Reload chain.json into memory and return True if it changed.

    Return: True if the chain was reloaded, False otherwise.
    """
    global _chain_mtime
    try:
        mtime = os.path.getmtime(CHAIN_FILE)
    except FileNotFoundError:
        return False
    if mtime != _chain_mtime:
        blockchain.load(CHAIN_FILE)
        _chain_mtime = mtime
        return True
    return False

def push_full_chain():
    """
    Send the whole chain to every connected browser tab.
    """
    payload = {"type": "INIT",
               "chain": [b.to_dict() for b in blockchain.blocks]}
    for q in subscribers:
        try: q.put_nowait(payload)
        except queue.Full: pass

def file_watcher():
    """
    Background thread: poll the file every second; push if changed.
    """
    while True:
        if sync_chain():
            push_full_chain()
        time.sleep(1)

def refresh_peers():
    """
    Background thread: poll the tracker every 5 seconds; update peer list.
    """
    global peer_list
    while True:
        try:
            r = requests.get(f"{TRACKER_URL}/peers", timeout=2)
            peer_list = [p for p in r.json() if p != PEER_ADDR]
        except requests.exceptions.RequestException:
            pass
        time.sleep(5)

def broadcast_block(bdict):
    """
    Broadcast a block to all connected peers.
    """
    for p in peer_list:
        host, port = p.rsplit(":", 1)
        ui_port    = str(int(port) + 100)
        for tgt in (f"{host}:{ui_port}", p):
            try:
                resp = requests.post(f"{tgt}/receive_block",
                                     json=bdict, timeout=1)
                if resp.ok:
                    break
            except requests.exceptions.RequestException:
                continue

@app.route("/")
def index():
    """
    Render the main HTML page.

    Return: The rendered HTML page.
    """
    return render_template("index.html", peer_id=PEER_PORT%10)

@app.route("/api/blocks")
def api_blocks():
    """
    Return the blockchain as a JSON object.

    Return: The blockchain as a JSON object.
    """
    return jsonify([b.to_dict() for b in blockchain.blocks])

@app.route("/api/block", methods=["POST"])
def api_mine():
    """
    Mine a new block.

    Return: The new block as a JSON object.
    """
    sync_chain()
    data = request.json or {}
    s, r_, art = data.get("sender"), data.get("recipient"), data.get("artwork_id")
    if not all([s, r_, art]):
        return {"error": "missing field"}, 400

    for b in blockchain.blocks:
        for t in b.transactions:
            if (t.sender == s and t.recipient == r_ and t.artwork_id == art):
                return {"error": f"Block #{b.header.block_num} already exists"}, 400

    tx  = Transaction(s, r_, art, ""); tx.sign(s)
    blk = blockchain.mine_next_block([tx])

    if blockchain.add_to_chain(blk):
        blockchain.save(CHAIN_FILE)
        bd = blk.to_dict()
        push_event = {"type": "BLOCK_ADDED", "block": bd}
        for q in subscribers: q.put_nowait(push_event)
        broadcast_block(bd)
        return {"status": "ok"}

    return {"error": "sender doesn't own the artwork"}, 400

@app.route("/receive_block", methods=["POST"])
def api_recv():
    """
    Receive a block from a peer.

    Return: The status of the block.
    """
    bd  = request.json
    blk = Block.from_dict(bd)

    sync_chain()
    if blockchain.add_to_chain(blk):
        blockchain.save(CHAIN_FILE)
        push_event = {"type": "BLOCK_ADDED", "block": bd}
        for q in subscribers: q.put_nowait(push_event)
        broadcast_block(bd)
        return {"status": "accepted"}, 200

    push_full_chain()
    return {"status": "duplicate"}, 200

@app.route("/stream")
def stream():
    """
    Stream the blockchain to the browser.

    Return: The stream of the blockchain.
    """
    def gen(q):
        q.put({"type": "INIT",
               "chain": [b.to_dict() for b in blockchain.blocks]})
        try:
            while True: yield f"data:{json.dumps(q.get())}\n\n"
        finally: subscribers.discard(q)

    q = queue.Queue(maxsize=10); subscribers.add(q)
    return Response(gen(q), mimetype="text/event-stream")

if __name__ == "__main__":
    import signal
    ap = argparse.ArgumentParser()
    ap.add_argument("--peer-port", type=int, required=True)
    ap.add_argument("--ui-port",   type=int, default=7201)
    ap.add_argument("--tracker",   required=True)
    args = ap.parse_args()

    PEER_PORT   = args.peer_port
    UI_PORT     = args.ui_port
    TRACKER_URL = args.tracker.rstrip("/")
    PEER_ADDR   = f"http://localhost:{PEER_PORT}"

    threading.Thread(target=file_watcher,  daemon=True).start()
    threading.Thread(target=refresh_peers, daemon=True).start()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.run(port=UI_PORT, threaded=True, debug=False)
