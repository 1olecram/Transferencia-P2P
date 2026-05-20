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

    def request_chunk(self, target_port, chunk_id, target_host='127.0.0.1'):
        """ Atua como Cliente: Conecta em outro Peer e pede um chunk específico. """
        
        # 1. Cria o socket para atuar como cliente
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            # 2. Inicia a conexão com a porta do outro Peer local
            print(f"[Peer] Solicitando chunk {chunk_id} para a porta {target_port}...")
            client_socket.connect((target_host, target_port))
            
            # 3. Formata e envia a requisição esperada pelo servidor
            request_msg = f"GET_CHUNK:{chunk_id}"
            client_socket.sendall(request_msg.encode('utf-8'))
            
            # 4. Recebe o arquivo em blocos
            received_data = b""
            while True:
                # Lê até 4096 bytes por vez. O recv vai bloquear até chegar dado.
                data_chunk = client_socket.recv(4096)
                
                # Se recv retornar vazio, significa que o servidor terminou de enviar e fechou a conexão
                if not data_chunk:
                    break
                    
                received_data += data_chunk
                
            # 5. Se recebemos algum dado, salvamos no disco
            if received_data:
                # Garante que a pasta 'parts' existe para não dar erro
                os.makedirs("parts", exist_ok=True)
                
                file_path = os.path.join("parts", f"chunk_{chunk_id}")
                with open(file_path, 'wb') as f:
                    f.write(received_data)
                    
                print(f"[Peer] Chunk {chunk_id} recebido e salvo com sucesso em '{file_path}'.")
            else:
                print(f"[Peer] O Peer na porta {target_port} não enviou dados para o chunk {chunk_id}.")
                
        except ConnectionRefusedError:
            print(f"[Peer] Falha: Ninguém ouvindo na porta {target_port}.")
        except Exception as e:
            print(f"[Peer] Erro durante a transferência com a porta {target_port}: {e}")
        finally:
            # 6. Sempre feche o socket do cliente após o uso
            client_socket.close()
