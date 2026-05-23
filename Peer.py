import socket
import threading
import os

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
    def __init__(self, host='0.0.0.0', port=5000):
        """Inicializa a configuração de rede e o socket do Peer.

        Cria um socket TCP/IP de fluxo (stream), aplica a opção de reuso de endereço
        (SO_REUSEADDR) para evitar bloqueios de porta após encerramentos rápidos e faz
        o bind para o host e porta especificados.

        Args:
            host (str, optional): IP de vinculação. Padrão é '0.0.0.0'.
            port (int, optional): Porta TCP para vinculação do servidor local. Padrão é 5000.
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.running = False
        
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
                
    def _handle_client(self, conn, addr):
        """Processa a requisição de um cliente conectado, enviando o chunk solicitado.

        Interpreta a mensagem enviada pelo cliente. A mensagem esperada segue o formato
        "GET_CHUNK:<id>". Caso o bloco físico correspondente exista localmente dentro
        da pasta de partes, o Peer lê o arquivo binário e o envia integralmente de volta
        ao cliente.

        Args:
            conn (socket.socket): O socket de conexão ativa com o cliente.
            addr (tuple): Uma tupla (IP, Porta) contendo os dados de endereço do cliente.
        """
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
        """Encerra com segurança o servidor P2P local.

        Desativa o loop de conexão principal definindo o flag `running` para falso e
        fecha o socket do servidor, forçando a liberação da porta TCP associada.
        """
        self.running = False
        self.server_socket.close()

    def request_chunk(self, target_port, chunk_id, target_host='127.0.0.1'):
        """Atua como cliente (Leecher) para solicitar e baixar um chunk específico de outro Peer.

        Cria um socket TCP temporário de cliente, conecta-se ao host e porta informados
        e envia a mensagem de protocolo estruturada ("GET_CHUNK:<id>"). Em seguida, recebe
        os dados em blocos sucessivos e salva o conteúdo de forma binária em um arquivo de bloco
        localmente dentro do diretório 'parts'.

        Args:
            target_port (int): A porta TCP do Peer destino ao qual se conectar.
            chunk_id (str ou int): O identificador do bloco do arquivo requisitado.
            target_host (str, optional): O endereço IP do Peer destino. Padrão é '127.0.0.1'.

        Raises:
            ConnectionRefusedError: Se o Peer destino não estiver executando ou não puder
                ser alcançado na porta especificada.
            Exception: Se ocorrer qualquer outro erro de rede, E/S ou transferência de dados.
        """
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
