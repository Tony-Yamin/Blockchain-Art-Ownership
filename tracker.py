import socket
import threading
import json
import time
import sys

PEER_INACTIVITY_LIMIT = 40
CLEANUP_INTERVAL = 10
peers_last_seen = {} 
peers_lock = threading.RLock()


def get_peer_overview():
    """
    Gather the current live peers.

    Returns:
        list of dict: each dict has keys "ip" (str) and "port" (int)
    """
    result = []
    with peers_lock:
        for (ip, port) in peers_last_seen:
            result.append({"ip": ip, "port": port})
        return result


def send_full_list_to(peer_socket):
    """
    After a new peer JOINs, reply with the complete, up-to-date peer list.

    Args:
        peer_socket (socket.socket): open connection to the joining peer
    """
    message = {
        "message_type": "PEER_LIST",
        "peers": get_peer_overview()
    }
    peer_socket.sendall((json.dumps(message) + "\n").encode())



def broadcast_list_update():
    """
    Tell every known peer about the latest peer list.
    """
    update = {
        "message_type": "PEER_UPDATE",
        "peers": get_peer_overview()
    }
    packet = (json.dumps(update) + "\n").encode()

    for (ip, port) in list(peers_last_seen):
        try:
            s = socket.create_connection((ip, port), timeout=3)
            s.sendall(packet)
            s.close()
        except:
            pass



def process_one_peer(peer_socket, address):
    """
    Handle exactly one message from a peer, then close.

    Reads a single JSON line, which must include:
      - "message_type": one of "JOIN", "LEAVE", or "KEEP_ALIVE"
      - "ip" and "port" of that peer

    Updates the peer table and notifies everyone if anything changed.

    Args:
        peer_socket (socket.socket): socket connected to the peer
        address (tuple): (ip, port) tuple assigned by accept()

    Returns:
        None
    """
    try:
        raw = peer_socket.recv(4096).decode().strip()
        info = json.loads(raw)
    except:
        peer_socket.close() 
        return 

    msg_type = info.get("message_type")
    peer_id  = (info.get("ip"), info.get("port"))
    now = time.time()

    #with peers_lock:
    if msg_type == "JOIN":
        peers_last_seen[peer_id] = now
        send_full_list_to(peer_socket)
        #print("[TRACKER] sent PEER_LIST", flush=True)
        time.sleep(0.1) 
    elif msg_type == "LEAVE":
        peers_last_seen.pop(peer_id, None)
    elif msg_type == "KEEP_ALIVE":
        peers_last_seen[peer_id] = now

    # Broadcast the new list to everyone if JOIN or LEAVE happened
    broadcast_list_update()
    peer_socket.close()



def remove_inactive_peers():
    """
    Periodically remove peers that haven’t sent a KEEP_ALIVE ping recently.
    """
    while True:
        time.sleep(CLEANUP_INTERVAL)
        now = time.time()
        removed = []
        with peers_lock:
            for peer, last_seen in list(peers_last_seen.items()):
                if now - last_seen > PEER_INACTIVITY_LIMIT:
                    removed.append(peer)
                    del peers_last_seen[peer]
        if removed:
            broadcast_list_update()



def start_tracker(port=8000):
    """
    Start listening for JOIN/LEAVE/KEEP_ALIVE messages on the given port.

    Args:
        port (int): TCP port number to bind to (default: 8000)

    Returns:
        None
    """
    # Launch the background janitor thread
    threading.Thread(target=remove_inactive_peers, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", port))
    server.listen()
    #print(f"[Tracker] Now listening on 0.0.0.0:{port}")

    try:
        while True:
            client_sock, client_addr = server.accept()
            threading.Thread(target=process_one_peer, args=(client_sock, client_addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[Tracker] Shutting down.")



if __name__ == "__main__":
    if len(sys.argv) > 1:
        chosen_port = int(sys.argv[1])
    else:
        chosen_port = 8000

    start_tracker(chosen_port)
