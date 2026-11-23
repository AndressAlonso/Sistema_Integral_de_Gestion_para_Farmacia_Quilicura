"""Buzón SMTP efímero de pruebas; nunca se conecta fuera de localhost."""
from contextlib import contextmanager
from socketserver import StreamRequestHandler, TCPServer
from threading import Thread


@contextmanager
def local_mailbox():
    captured = []

    class Handler(StreamRequestHandler):
        def handle(self):
            self.wfile.write(b"220 localhost QA\r\n")
            while line := self.rfile.readline():
                command = line.split(b" ", 1)[0].strip().upper()
                if command in (b"EHLO", b"HELO"):
                    self.wfile.write(b"250 localhost\r\n")
                elif command == b"DATA":
                    self.wfile.write(b"354 End with dot\r\n")
                    data = []
                    while (chunk := self.rfile.readline()) not in (b".\r\n", b""):
                        data.append(chunk[1:] if chunk.startswith(b"..") else chunk)
                    captured.append(b"".join(data))
                    self.wfile.write(b"250 Accepted locally\r\n")
                elif command == b"QUIT":
                    self.wfile.write(b"221 Bye\r\n")
                    return
                else:
                    self.wfile.write(b"250 OK\r\n")

    with TCPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1], captured
        finally:
            server.shutdown()
            thread.join(timeout=5)
