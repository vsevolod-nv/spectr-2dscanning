import socket
import time
import matplotlib.pyplot as plt


def recv_message(sock, timeout=1):
    sock.settimeout(timeout)
    msg = ""
    while True:
        try:
            char = sock.recv(1).decode("ascii")
            if not char:
                break
            msg += char
            if char == ">":
                return msg
        except socket.timeout:
            return None


def main():
    HOST, PORT = "127.0.0.1", 50009

    with socket.socket() as s:
        s.connect((HOST, PORT))
        s.sendall(b"c0>")
        time.sleep(0.1)
        s.sendall(b"#exp=10>")
        time.sleep(0.2)
        s.sendall(b"s>")

        data_msg = None
        timeout = 5
        start = time.time()
        while time.time() - start < timeout:
            msg = recv_message(s, timeout=1)
            if msg and msg.startswith("<"):
                data_msg = msg
                break

        s.sendall(b"d>")

    if not data_msg:
        return

    clean = data_msg.strip("<>")
    values = list(map(float, clean.split()))
    x = values[::2]
    y = values[1::2]

    plt.figure(figsize=(10, 4))
    plt.plot(x, y, "-b")
    plt.title("Single shot spectrum")
    plt.xlabel("Wavenumber (1/cm)")
    plt.ylabel("Intensity")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()