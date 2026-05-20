import socket
import threading
import os

class Peer:
    def __init__(self, host='0.0.0.0', port=5000):
        """
        Configuração de network e portas
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.running = False
        
    def start_listening(self):
        self.running = True
        self.server_socket.listen(5)
        print(f"[Peer] Ouvindo na porta {self.port}...")
        
        # Inicia a thread principal que aceitará conexões
        listen_thread = threading.Thread(target=self._accept_connections)
        listen_thread.daemon = True
        listen_thread.start()
        
    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                # Para cada conexão, inicia uma nova thread
                client_thread = threading.Thread(target=self._handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
            except OSError:
                # Ocorre normalmente quando o socket é fechado pelo método stop()
                break
                
    def _handle_client(self, conn, addr):
        with conn:
            try:
                # Recebe a requisição do cliente
                data = conn.recv(1024).decode('utf-8').strip()
                
                if data.startswith("GET_CHUNK:"):
                    chunk_id = data.split(":")[1]
                    file_path = os.path.join("parts", f"chunk_{chunk_id}")
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            chunk_data = f.read()
                        conn.sendall(chunk_data)
                        print(f"[Peer] Chunk {chunk_id} enviado para {addr}")
                    else:
                        print(f"[Peer] Arquivo não encontrado: {file_path}")
            except Exception as e:
                print(f"[Peer] Erro na conexão com {addr}: {e}")

    def stop(self):
        self.running = False
        self.server_socket.close()
