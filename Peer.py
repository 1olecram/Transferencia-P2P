import socket
import threading
import os
import hashlib
import time
from FileMetadata import FileMetadata

class Peer:
    """Representa um nó (Peer) P2P que atua como Cliente e Servidor em memória.

    Esta classe gerencia a escuta TCP paralela e a sincronização automática de chunks.
    """

    def __init__(self, port, vizinhos, storage_dir="parts", host='0.0.0.0', metadata=None, blocks_present=None, original_file_path=None):
        """Inicializa as configurações de rede e dados do Peer.

        Args:
            port (int): Porta TCP local para escuta.
            vizinhos (list[int]): Lista de portas TCP dos vizinhos.
            storage_dir (str): Diretório físico para gravação do arquivo final.
            host (str): IP de vinculação da escuta local.
            metadata (dict, optional): Metadados estruturados do arquivo original.
            blocks_present (list[bool], optional): Array de progresso dos blocos.
            original_file_path (str, optional): Caminho do arquivo original caso seja Seeder.
        """
        self.host = host
        self.port = port
        self.vizinhos = vizinhos
        self.storage_dir = storage_dir
        self.metadata = metadata
        self.blocks_present = blocks_present
        self.original_file_path = original_file_path
        self.downloaded_chunks = {}
        self.running = False
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        
        if self.original_file_path and os.path.exists(self.original_file_path) and self.metadata:
            self.blocks_present = [True] * self.metadata["num_blocks"]

    def validate_and_update_blocks(self):
        """Valida a existência e integridade do arquivo final local.

        Returns:
            list[bool]: Array booleano indicando a presença dos chunks locais.
        """
        if not self.metadata:
            return []
        self.blocks_present = [False] * self.metadata["num_blocks"]
        self.downloaded_chunks = {}
        
        if self.original_file_path and os.path.exists(self.original_file_path):
            self.blocks_present = [True] * len(self.blocks_present)
            return self.blocks_present
            
        final_path = os.path.join(self.storage_dir, self.metadata["original_name"])
        if os.path.exists(final_path):
            try:
                with open(final_path, 'rb') as f:
                    content = f.read()
                if hashlib.sha256(content).hexdigest() == self.metadata["file_hash"]:
                    cs = self.metadata["chunk_size"]
                    self.downloaded_chunks = {i: content[i*cs : (i+1)*cs] for i in range(self.metadata["num_blocks"])}
                    self.blocks_present = [True] * len(self.blocks_present)
                    print(f"[Peer:{self.port}] Arquivo final '{self.metadata['original_name']}' já validado localmente.")
            except Exception as e:
                print(f"[Peer:{self.port}] Falha ao ler/validar arquivo local: {e}")
        return self.blocks_present

    def start_listening(self):
        """Inicializa a thread daemon de escuta TCP para conexões de vizinhos."""
        self.running = True
        self.server_socket.listen(15)
        threading.Thread(target=self._accept_connections, daemon=True).start()

    def _accept_connections(self):
        """Loop executado em segundo plano para aceitar conexões de rede."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except OSError:
                break

    def get_chunk_bytes(self, chunk_id):
        """Lê os bytes de um chunk do arquivo original ou da memória.

        Args:
            chunk_id (int): ID do chunk requisitado.

        Returns:
            bytes: Dados binários do chunk.
        """
        if self.original_file_path and os.path.exists(self.original_file_path) and self.metadata:
            with open(self.original_file_path, 'rb') as f:
                f.seek(chunk_id * self.metadata["chunk_size"])
                return f.read(self.metadata["chunk_size"])
        return self.downloaded_chunks.get(chunk_id, b"")

    def _handle_client(self, conn, addr):
        """Processa requisições de um cliente conectado de forma persistente.

        Args:
            conn (socket.socket): Socket ativo da conexão com o cliente.
            addr (tuple): Dados de endereço (IP, Porta) do cliente conectado.
        """
        with conn:
            conn.settimeout(5.0)
            while self.running:
                try:
                    data = conn.recv(1024).decode('utf-8').strip()
                    if not data:
                        break
                    if data == "GET_AVAILABLE_CHUNKS":
                        if self.original_file_path and os.path.exists(self.original_file_path) and self.metadata:
                            cids = list(range(self.metadata["num_blocks"]))
                        else:
                            cids = list(self.downloaded_chunks.keys())
                        conn.sendall(",".join(str(c) for c in cids).encode('utf-8'))
                        break
                    elif data.startswith("GET_CHUNK:"):
                        chunk_id = int(data.split(":")[1])
                        chunk_data = self.get_chunk_bytes(chunk_id)
                        if chunk_data:
                            conn.sendall(chunk_data)
                        else:
                            break
                except Exception:
                    break

    def request_available_chunks(self, target_port, target_host='127.0.0.1'):
        """Solicita a lista de chunks disponíveis de um nó vizinho.

        Args:
            target_port (int): Porta TCP do vizinho.
            target_host (str): Endereço IP do vizinho.

        Returns:
            list[int]: Lista de IDs de chunks disponíveis, ou None em caso de falha.
        """
        try:
            with socket.create_connection((target_host, target_port), timeout=2.0) as s:
                s.sendall(b"GET_AVAILABLE_CHUNKS")
                s.shutdown(socket.SHUT_WR)
                received = b""
                while True:
                    data = s.recv(65536)
                    if not data:
                        break
                    received += data
                res = received.decode('utf-8').strip()
                return [int(c) for c in res.split(",") if c.isdigit()] if res else []
        except Exception:
            return None

    def _recv_chunk_from_socket(self, sock, chunk_id):
        """Lê os bytes de um chunk diretamente de um socket de forma precisa.

        Args:
            sock (socket.socket): Socket conectado.
            chunk_id (int): ID do chunk esperado.

        Returns:
            bytes: Dados binários lidos, ou vazio em caso de falha.
        """
        if not self.metadata:
            return b""
        received = b""
        expected = self.metadata["chunk_size"]
        if chunk_id == self.metadata["num_blocks"] - 1:
            expected = self.metadata["total_size"] - (chunk_id * self.metadata["chunk_size"])
        while len(received) < expected:
            data = sock.recv(min(4096, expected - len(received)))
            if not data:
                break
            received += data
        return received if len(received) == expected else b""

    def request_chunk(self, target_port, chunk_id, target_host='127.0.0.1'):
        """Solicita e baixa um único chunk de um vizinho em uma conexão curta.

        Args:
            target_port (int): Porta TCP do vizinho.
            chunk_id (int): ID do chunk requisitado.
            target_host (str): Endereço IP do vizinho.

        Returns:
            bool: True se o download foi bem-sucedido, False caso contrário.
        """
        try:
            with socket.create_connection((target_host, target_port), timeout=2.0) as s:
                s.sendall(f"GET_CHUNK:{chunk_id}".encode('utf-8'))
                data = self._recv_chunk_from_socket(s, chunk_id)
                if data:
                    self.downloaded_chunks[chunk_id] = data
                    return True
        except Exception:
            pass
        return False

    def test_neighbor_connection(self, port, host='127.0.0.1'):
        """Realiza um teste rápido de conexão TCP com um vizinho.

        Args:
            port (int): Porta TCP do vizinho.
            host (str): Endereço IP do vizinho.

        Returns:
            bool: True se conectou, False caso contrário.
        """
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except Exception:
            return False

    def get_neighbor_statuses(self, host='127.0.0.1'):
        """Testa a conectividade com todos os vizinhos configurados.

        Args:
            host (str): Endereço IP comum de destino.

        Returns:
            dict[int, bool]: Mapeamento de porta para status de conectividade.
        """
        return {port: self.test_neighbor_connection(port, host) for port in self.vizinhos}

    def download_chunk_manually(self, target_port, chunk_id):
        """Gerencia o download manual e validação SHA-256 de um bloco de arquivo.

        Args:
            target_port (int): Porta TCP do vizinho de origem.
            chunk_id (int): ID do chunk requisitado.

        Returns:
            bool: True se o bloco foi validado, False caso contrário.
        """
        if not self.metadata or self.blocks_present is None:
            return False
        if self.request_chunk(target_port, chunk_id):
            chunk_data = self.downloaded_chunks[chunk_id]
            if hashlib.sha256(chunk_data).hexdigest() == self.metadata["block_hashes"][chunk_id]:
                self.blocks_present[chunk_id] = True
                print(f"[Peer:{self.port}] Chunk {chunk_id} recebido com sucesso da porta {target_port} e validado.")
                if all(self.blocks_present):
                    self.reconstruct_file()
                return True
            else:
                del self.downloaded_chunks[chunk_id]
        return False

    def run_automatic_download(self, progress_callback=None):
        """Executa o fluxo de download automático e persistente de todos os chunks.

        Args:
            progress_callback (callable, optional): Função de retorno para exibir progresso.
        """
        if not self.metadata or self.blocks_present is None:
            return
        num_blocks = self.metadata["num_blocks"]
        block_hashes = self.metadata["block_hashes"]
        print(f"\n[Peer:{self.port}] Iniciando download automático de {num_blocks} blocos...")

        while not all(self.blocks_present) and self.running:
            online_neighbors = {}
            for port in self.vizinhos:
                avail = self.request_available_chunks(port)
                if avail is not None:
                    online_neighbors[port] = avail

            if not online_neighbors:
                time.sleep(0.5)
                continue

            made_progress = False
            for port, avail_chunks in online_neighbors.items():
                needed = [i for i in avail_chunks if not self.blocks_present[i]]
                if not needed:
                    continue
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=5.0) as s:
                        for cid in needed:
                            if self.blocks_present[cid]:
                                continue
                            s.sendall(f"GET_CHUNK:{cid}".encode('utf-8'))
                            received = self._recv_chunk_from_socket(s, cid)
                            if received and hashlib.sha256(received).hexdigest() == block_hashes[cid]:
                                self.downloaded_chunks[cid] = received
                                self.blocks_present[cid] = True
                                made_progress = True
                                print(f"[Peer:{self.port}] Bloco {cid} recebido com sucesso da fonte (porta {port}) e validado.")
                            else:
                                break
                except Exception:
                    pass

            if progress_callback:
                progress_callback()

            if not made_progress and not all(self.blocks_present):
                time.sleep(0.5)

        if all(self.blocks_present):
            self.reconstruct_file()

    def reconstruct_file(self):
        """Reconstrói o arquivo final no sistema local.

        Returns:
            tuple[bool, str]: Status de sucesso e mensagem.
        """
        if not self.metadata:
            return False, "[Erro] Nenhum metadado carregado."
        final_path = os.path.join(self.storage_dir, self.metadata["original_name"])
        success, msg = FileMetadata.reconstruct_file(final_path, self.downloaded_chunks, self.metadata)
        print(f"[Peer:{self.port}] {msg}")
        return success, msg

    def load_metadata(self, metadata):
        """Carrega e registra metadados de arquivo no Peer.

        Args:
            metadata (dict): Estrutura de metadados do arquivo.
        """
        self.metadata = metadata
        self.validate_and_update_blocks()

    def stop(self):
        """Encerra com segurança o nó P2P local."""
        self.running = False
        try:
            self.server_socket.close()
        except Exception:
            pass
