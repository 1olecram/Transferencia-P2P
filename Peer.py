import socket
import threading
import os
import hashlib
import time
from FileMetadata import FileMetadata

class Peer:
    """Representa um nó (Peer) em uma rede de transferência de arquivos P2P.

    Um Peer nesta rede híbrida atua simultaneamente como um servidor (Seeder),
    ouvindo conexões de rede em uma thread dedicada para fornecer blocos (chunks)
    de arquivos que possui localmente, e como um cliente (Leecher), conectando-se
    a outros Peers ativos para solicitar blocos específicos de arquivos.

    Attributes:
        host (str): O endereço de IP que o Peer usará para se ligar na rede.
            Padrão é '0.0.0.0' para aceitar conexões em todas as interfaces de rede.
        port (int): A porta TCP específica na qual o Peer irá escutar conexões de entrada.
        server_socket (socket.socket): O socket TCP principal configurado para escuta.
        running (bool): Flag de controle indicando se o servidor P2P local está ativo.
    """
    def __init__(self, port, vizinhos, storage_dir="parts", host='0.0.0.0', metadata=None, blocks_present=None):
        """Inicializa a configuração de rede, o diretório de armazenamento e o socket do Peer.

        Cria um socket TCP/IP de fluxo (stream), aplica a opção de reuso de endereço
        (SO_REUSEADDR) para evitar bloqueios de porta após encerramentos rápidos e faz
        o bind para o host e porta especificados.

        Args:
            port (int): Porta TCP para vinculação do servidor local.
            vizinhos (list[int]): Lista de portas dos nós vizinhos.
            storage_dir (str, optional): Diretório físico onde os chunks deste Peer serão
                salvos ou de onde serão lidos. Padrão é "parts".
            host (str, optional): IP de vinculação. Padrão é '0.0.0.0'.
            metadata (dict, optional): Metadados estruturados do arquivo.
            blocks_present (list[bool], optional): Array de progresso dos blocos.
        """
        self.host = host
        self.port = port
        self.vizinhos = vizinhos
        self.storage_dir = storage_dir
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.running = False
        self.metadata = metadata
        self.blocks_present = blocks_present
        
    def start_listening(self):
        """Ativa o servidor P2P e inicia a thread dedicada para escuta de conexões de entrada.

        Coloca o socket local em modo de escuta (listening) com limite de fila de conexões pendentes.
        Posteriormente, dispara de maneira assíncrona (em segundo plano) uma thread daemonizada
        responsável por aceitar conexões contínuas sem bloquear a execução principal.
        """
        self.running = True
        self.server_socket.listen(5)
        print(f"[Peer] Ouvindo na porta {self.port}...")
        
        # Inicia a thread principal que aceitará conexões
        listen_thread = threading.Thread(target=self._accept_connections)
        listen_thread.daemon = True
        listen_thread.start()
        
    def _accept_connections(self):
        """Loop contínuo de escuta para aceitar novas conexões de entrada de outros Peers.

        Executa de forma ininterrupta enquanto o Peer estiver ativo (`self.running == True`).
        Ao receber uma nova conexão de cliente, delega o atendimento para uma thread
        daemonizada secundária, garantindo concorrência e que múltiplos leechers possam
        baixar blocos ao mesmo tempo.

        Raises:
            OSError: Captura silenciosamente erros de socket quando o socket é fechado
                intencionalmente através do método `stop()`.
        """
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
                
    def get_available_chunks(self):
        """Escaneia o diretório de armazenamento e lista os chunks disponíveis.

        Varre o diretório configurado em `storage_dir` buscando por arquivos que
        iniciam com o prefixo 'chunk_'. Para cada um encontrado, extrai a identificação
        numérica do chunk.

        Returns:
            list[int]: Lista ordenada contendo os IDs dos chunks que este Peer
                possui localmente.
        """
        chunks = []
        if os.path.exists(self.storage_dir):
            for name in os.listdir(self.storage_dir):
                if name.startswith("chunk_"):
                    try:
                        chunk_id = int(name.split("_")[1])
                        chunks.append(chunk_id)
                    except (ValueError, IndexError):
                        pass
        chunks.sort()
        return chunks

    def _handle_client(self, conn, addr):
        """Processa a requisição de um cliente conectado, enviando o chunk solicitado.

        Interpreta a mensagem enviada pelo cliente.
        Suporta os seguintes comandos:
        - "GET_AVAILABLE_CHUNKS": Retorna uma lista de IDs de chunks disponíveis separada por vírgula.
        - "GET_CHUNK:<id>": Caso o bloco físico correspondente exista localmente dentro
          da pasta configurada, lê o arquivo binário e o envia de volta ao cliente.

        Args:
            conn (socket.socket): O socket de conexão ativa com o cliente.
            addr (tuple): Uma tupla (IP, Porta) contendo os dados de endereço do cliente.
        """
        with conn:
            try:
                # Recebe a requisição do cliente
                data = conn.recv(1024).decode('utf-8').strip()
                
                if data == "GET_AVAILABLE_CHUNKS":
                    available = self.get_available_chunks()
                    response = ",".join(str(cid) for cid in available)
                    conn.sendall(response.encode('utf-8'))
                    
                elif data.startswith("GET_CHUNK:"):
                    chunk_id = data.split(":")[1]
                    file_path = os.path.join(self.storage_dir, f"chunk_{chunk_id}")
                    
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
        """Encerra com segurança o servidor P2P local.

        Desativa o loop de conexão principal definindo o flag `running` para falso e
        fecha o socket do servidor, forçando a liberação da porta TCP associada.
        """
        self.running = False
        self.server_socket.close()

    def request_available_chunks(self, target_port, target_host='127.0.0.1'):
        """Solicita a lista de chunks disponíveis de um nó vizinho.

        Conecta-se ao socket TCP do Peer destino na porta especificada e envia
        a requisição 'GET_AVAILABLE_CHUNKS'. Aguarda o retorno da lista de chunks
        e a decodifica de volta em uma lista de inteiros.

        Args:
            target_port (int): Porta TCP do Peer vizinho.
            target_host (str, optional): Endereço IP do Peer vizinho. Padrão é '127.0.0.1'.

        Returns:
            list[int]: Lista contendo os IDs dos chunks disponíveis no vizinho,
                ou uma lista vazia em caso de falha de conexão ou ausência de blocos.
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(1.5)
        try:
            client_socket.connect((target_host, target_port))
            client_socket.sendall(b"GET_AVAILABLE_CHUNKS")
            response = client_socket.recv(4096).decode('utf-8').strip()
            if not response:
                return []
            return [int(cid) for cid in response.split(",") if cid.isdigit()]
        except (ConnectionRefusedError, socket.timeout, OSError):
            return []
        except Exception as e:
            print(f"[Peer] Erro ao obter chunks disponíveis do vizinho {target_port}: {e}")
            return []
        finally:
            client_socket.close()

    def request_chunk(self, target_port, chunk_id, target_host='127.0.0.1'):
        """Atua como cliente (Leecher) para solicitar e baixar um chunk específico de outro Peer.

        Cria um socket TCP temporário de cliente, conecta-se ao host e porta informados
        e envia a mensagem de protocolo estruturada ("GET_CHUNK:<id>"). Em seguida, recebe
        os dados em blocos sucessivos e salva o conteúdo de forma binária em um arquivo de bloco
        localmente dentro do diretório configurado.

        Args:
            target_port (int): A porta TCP do Peer destino ao qual se conectar.
            chunk_id (str ou int): O identificador do bloco do arquivo requisitado.
            target_host (str, optional): O endereço IP do Peer destino. Padrão é '127.0.0.1'.

        Returns:
            bool: True se o download foi bem-sucedido, False caso contrário.
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(3.0)
        success = False
        try:
            print(f"[Peer] Solicitando chunk {chunk_id} para a porta {target_port}...")
            client_socket.connect((target_host, target_port))
            
            request_msg = f"GET_CHUNK:{chunk_id}"
            client_socket.sendall(request_msg.encode('utf-8'))
            
            received_data = b""
            while True:
                data_chunk = client_socket.recv(4096)
                if not data_chunk:
                    break
                received_data += data_chunk
                
            if received_data:
                os.makedirs(self.storage_dir, exist_ok=True)
                file_path = os.path.join(self.storage_dir, f"chunk_{chunk_id}")
                with open(file_path, 'wb') as f:
                    f.write(received_data)
                print(f"[Peer] Chunk {chunk_id} recebido e salvo com sucesso em '{file_path}'.")
                success = True
            else:
                print(f"[Peer] O Peer na porta {target_port} não enviou dados para o chunk {chunk_id}.")
                
        except ConnectionRefusedError:
            print(f"[Peer] Falha: Ninguém ouvindo na porta {target_port}.")
        except Exception as e:
            print(f"[Peer] Erro durante a transferência com a porta {target_port}: {e}")
        finally:
            client_socket.close()
        return success

    def test_neighbor_connection(self, port, host='127.0.0.1', timeout=1.5):
        """Realiza uma tentativa rápida de conexão TCP com um vizinho para testar se ele está online.

        Abre um socket temporário de baixo tempo de espera (timeout) para evitar bloqueios longos.

        Args:
            port (int): A porta TCP do nó vizinho.
            host (str, optional): O endereço IP do vizinho. Padrão é '127.0.0.1'.
            timeout (float, optional): Tempo máximo em segundos para esperar a conexão. Padrão é 1.5.

        Returns:
            bool: True se a conexão foi estabelecida com sucesso, False caso contrário.
        """
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(timeout)
        try:
            test_socket.connect((host, port))
            test_socket.close()
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

    def get_neighbor_statuses(self, host='127.0.0.1'):
        """Testa e retorna de forma estruturada o status de conexão de todos os vizinhos.

        Args:
            host (str, optional): O endereço IP de destino dos testes. Padrão é '127.0.0.1'.

        Returns:
            dict[int, bool]: Um dicionário mapeando cada porta de vizinho a um booleano de conectividade.
        """
        statuses = {}
        for port in self.vizinhos:
            statuses[port] = self.test_neighbor_connection(port, host=host)
        return statuses

    def validate_and_update_blocks(self):
        """Valida os chunks já existentes localmente contra os hashes de metadados.

        Varre o diretório configurado, verifica a validade SHA-256 e limpa chunks inválidos.

        Returns:
            list[bool]: Array booleano atualizado correspondente à presença e
                validez dos chunks no diretório local.
        """
        if self.metadata is None:
            return []

        num_blocks = self.metadata["num_blocks"]
        block_hashes = self.metadata["block_hashes"]
        self.blocks_present = [False] * num_blocks

        if not os.path.exists(self.storage_dir):
            return self.blocks_present

        for i in range(num_blocks):
            chunk_path = os.path.join(self.storage_dir, f"chunk_{i}")
            if os.path.exists(chunk_path):
                try:
                    with open(chunk_path, 'rb') as f:
                        content = f.read()
                    chunk_hash = hashlib.sha256(content).hexdigest()
                    if chunk_hash == block_hashes[i]:
                        self.blocks_present[i] = True
                    else:
                        os.remove(chunk_path)
                        print(f"[Aviso] Chunk {i} corrompido ou inválido removido.")
                except Exception as e:
                    print(f"[Aviso] Erro ao ler/validar chunk {i}: {e}")

        return self.blocks_present

    def reconstruct_file(self):
        """Reconstrói o arquivo original usando os chunks salvos e a classe FileMetadata.

        Returns:
            tuple[bool, str]: Uma tupla (sucesso, mensagem de status/erro).
        """
        if self.metadata is None:
            return False, "[Erro] Nenhum metadado carregado."
        return FileMetadata.reconstruct_file(self.storage_dir, self.metadata)

    def load_metadata(self, metadata):
        """Carrega novos metadados no Peer e revalida os blocos locais."""
        self.metadata = metadata
        self.validate_and_update_blocks()

    def download_chunk_manually(self, target_port, chunk_id):
        """Requisita manualmente um chunk de uma porta específica e realiza validações SHA-256.

        Args:
            target_port (int): Porta do peer de destino.
            chunk_id (int): Identificador do chunk.

        Returns:
            bool: True se o download e validação foram bem-sucedidos, False caso contrário.
        """
        success = self.request_chunk(target_port=target_port, chunk_id=chunk_id)
        if success and self.metadata is not None and self.blocks_present is not None:
            chunk_path = os.path.join(self.storage_dir, f"chunk_{chunk_id}")
            if os.path.exists(chunk_path):
                try:
                    with open(chunk_path, 'rb') as f:
                        content = f.read()
                    chunk_hash = hashlib.sha256(content).hexdigest()
                    if chunk_id < len(self.metadata["block_hashes"]) and chunk_hash == self.metadata["block_hashes"][chunk_id]:
                        self.blocks_present[chunk_id] = True
                        print(f"[Sucesso] Chunk {chunk_id} validado com sucesso!")
                        if all(self.blocks_present):
                            success_recon, msg = self.reconstruct_file()
                            print(msg)
                        return True
                    else:
                        print(f"[Erro] Chunk {chunk_id} corrompido! Hash inválido.")
                        os.remove(chunk_path)
                except Exception as e:
                    print(f"[Erro] Falha ao processar/validar chunk {chunk_id}: {e}")
        return False

    def run_automatic_download(self, progress_callback=None):
        """Executa o processo automatizado de download de chunks de vizinhos ativos.

        Varre os vizinhos ativos mapeando os chunks que cada um possui e solicita
        de forma eficiente apenas os que faltam localmente, atualizando o array
        booleano após a validação SHA-256 de cada pedaço.

        Args:
            progress_callback (callable, optional): Callback de interface para renderização
                do progresso visual.
        """
        if self.metadata is None:
            print("[Erro] Nenhum metadado carregado. Carregue um metadado primeiro.")
            return

        if self.blocks_present is None:
            print("[Erro] Estado de progresso dos blocos não inicializado.")
            return

        num_blocks = self.metadata["num_blocks"]
        block_hashes = self.metadata["block_hashes"]

        print("\n" + "=" * 60)
        print(" INICIANDO DOWNLOAD P2P AUTOMATIZADO ".center(60, "="))
        print("=" * 60)

        if progress_callback:
            progress_callback()

        while not all(self.blocks_present):
            online_neighbors = {}
            for port in self.vizinhos:
                print(f"[Download] Consultando vizinho na porta {port}...")
                available = self.request_available_chunks(port)
                if available is not None and len(available) > 0 or available == []:
                    online_neighbors[port] = available
                    print(f" -> Vizinho {port} online com {len(available)} chunks disponíveis.")
                else:
                    if self.test_neighbor_connection(port):
                        online_neighbors[port] = []
                        print(f" -> Vizinho {port} online, mas sem chunks no momento.")
                    else:
                        print(f" -> Vizinho {port} offline.")

            if not online_neighbors:
                print("\n[Aviso] Nenhum vizinho ativo com chunks encontrado. Aguardando 3 segundos...")
                time.sleep(3)
                continue

            downloaded_in_iteration = 0

            for i in range(num_blocks):
                if self.blocks_present[i]:
                    continue

                possible_sources = [port for port, chunks in online_neighbors.items() if i in chunks]

                if possible_sources:
                    source_port = possible_sources[0]
                    print(f"[Download] Baixando chunk {i} do vizinho {source_port}...")

                    if self.request_chunk(target_port=source_port, chunk_id=i):
                        chunk_path = os.path.join(self.storage_dir, f"chunk_{i}")
                        try:
                            with open(chunk_path, 'rb') as f:
                                content = f.read()
                            chunk_hash = hashlib.sha256(content).hexdigest()
                            if chunk_hash == block_hashes[i]:
                                self.blocks_present[i] = True
                                downloaded_in_iteration += 1
                                print(f"[Download] Chunk {i} baixado e validado com sucesso!")
                            else:
                                print(f"[Erro] Falha de integridade no chunk {i}! Hash incorreto.")
                                os.remove(chunk_path)
                        except Exception as e:
                            print(f"[Erro] Falha ao processar/validar chunk {i}: {e}")

            if downloaded_in_iteration == 0 and not all(self.blocks_present):
                print("\n[Aviso] Nenhum progresso feito nesta iteração. Alguns chunks podem não estar disponíveis.")
                print("Aguardando 3 segundos antes de tentar novamente...")
                time.sleep(3)

            if progress_callback:
                progress_callback()

        print("\n" + "=" * 60)
        print(" DOWNLOAD CONCLUÍDO COM SUCESSO! ".center(60, "="))
        print("=" * 60)

        success_recon, msg = self.reconstruct_file()
        print(msg)

