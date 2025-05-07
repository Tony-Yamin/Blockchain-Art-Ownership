import argparse, subprocess, sys, time, signal

def pop(cmd):
    """
    Run a command and return the process.

    Args:
        cmd (list): The command to run.

    Returns:
        subprocess.Popen: The process.
    """
    return subprocess.Popen(
        ["python", "-u", *cmd[1:]],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )


def main():
    """
    Run the network.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--num-peers", type=int, default=3)
    ap.add_argument("-b", "--base-port", type=int, default=7000)
    args = ap.parse_args()

    BASE, N = args.base_port, args.num_peers
    procs = []

    try:
        tracker_port = BASE
        procs.append(pop(["python", "tracker.py", "--port", str(tracker_port)]))
        print(f"Tracker      → http://localhost:{tracker_port}")
        time.sleep(1)

        for i in range(N):
            peer_port = BASE + 101 + i
            ui_port   = BASE + 201 + i
            tracker   = f"http://localhost:{tracker_port}"

            procs.append(pop([
                "python", "peer.py",
                "--port", str(peer_port),
                "--tracker", tracker
            ]))
            procs.append(pop([
                "python", "ui.py",
                "--peer-port", str(peer_port),
                "--ui-port",   str(ui_port),
                "--tracker",   tracker
            ]))

            print(f"Peer {i+1:>2} UI  → http://localhost:{ui_port}  (peer :{peer_port})")

        print("\nNetwork up. Ctrl‑C to stop.\n")

        while True:
            for p in procs:
                line = p.stdout.readline()
                if line:
                    sys.stdout.buffer.write(line)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")
        for p in procs:
            try: p.send_signal(signal.SIGINT)
            except Exception: pass
        for p in procs: p.wait()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()
