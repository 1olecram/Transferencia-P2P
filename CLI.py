"""Módulo contendo a interface de linha de comando (CLI) para nós P2P.

Este módulo define a classe `CLI`, que gerencia unicamente a interface interativa
do terminal de usuário do nó P2P (comandos, ajuda, menus e exibição de progresso).
"""

import os
import sys


class CLI:
    """Gerencia a interface de linha de comando e interação do usuário com o nó P2P.

    Esta classe é responsável apenas pela entrada de comandos do usuário no terminal
    e pela apresentação visual formatada do status do nó e progresso do download.
    """

    def __init__(self, peer):
        """Inicializa a CLI associando-a a um nó Peer ativo.

        Args:
            peer (Peer): Instância do nó Peer que executa as funções de rede e lógica de dados.
        """
        self.peer = peer

    def show_network_status(self, host='127.0.0.1'):
        """Testa e exibe de forma formatada o status de conexão de todos os vizinhos.

        Args:
            host (str, optional): O endereço IP de destino dos testes. Padrão é '127.0.0.1'.
        """
        print("\n" + "=" * 50)
        print(" STATUS DE CONEXÃO DOS VIZINHOS ".center(50, "="))
        print("=" * 50)
        
        statuses = self.peer.get_neighbor_statuses(host=host)
        for idx, (port, is_online) in enumerate(statuses.items(), 1):
            print(f"[Vizinho {idx}] Tentando conectar à porta {port}...")
            if is_online:
                print(f" -> STATUS: [ ONLINE ] (Conexão bem-sucedida com a porta {port})")
            else:
                print(f" -> STATUS: [ OFFLINE ] (Não foi possível conectar à porta {port})")
        print("=" * 50 + "\n")

    def show_blocks_progress(self):
        """Exibe de forma visual o progresso de download dos blocos locais."""
        if not self.peer.metadata or self.peer.blocks_present is None:
            print("[Status] Nenhum metadado carregado.")
            return

        num_blocks = len(self.peer.blocks_present)
        downloaded = sum(self.peer.blocks_present)
        percentage = (downloaded / num_blocks) * 100

        visual = ["[x]" if val else "[ ]" for val in self.peer.blocks_present]

        print(f"\nProgresso: {downloaded}/{num_blocks} blocos ({percentage:.1f}%)")
        print(" ".join(visual))

    def run(self):
        """Inicia a CLI interativa e o processamento de comandos do usuário no terminal."""
        if self.peer is None:
            print("[Erro] Peer local não inicializado.")
            return

        print(f"\n[Peer CLI] Testando conexão com vizinhos...")
        self.show_network_status()

        print("=" * 60)
        print(" TERMINAL INTERATIVO DO NÓ P2P UNIFICADO (CLASS CLI) ".center(60, " "))
        print("=" * 60)
        print("Comandos disponíveis:")
        print("  status                  - Verifica status de conexão dos vizinhos.")
        print("  blocks                  - Mostra array de progresso de blocos locais.")
        print("  get <chunk_id> <porta>  - Requisita manualmente um chunk de uma porta específica.")
        print("  download                - Inicia a transferência P2P automática de vizinhos ativos.")
        print("  load_metadata <caminho> - Carrega um arquivo JSON de metadados de arquivo.")
        print("  help                    - Mostra este menu de ajuda novamente.")
        print("  exit / quit             - Encerra o nó com segurança.")
        print("=" * 60)

        try:
            while True:
                command_line = input(f"\n[Peer:{self.peer.port}]> ").strip()
                if not command_line:
                    continue

                parts = command_line.split()
                cmd = parts[0].lower()

                if cmd in ("exit", "quit"):
                    print("\n[Peer CLI] Encerrando nó P2P local...")
                    break

                elif cmd == "status":
                    self.show_network_status()

                elif cmd == "blocks":
                    self.show_blocks_progress()

                elif cmd == "help":
                    print("\nComandos disponíveis:")
                    print("  status                  - Verifica status de conexão dos vizinhos.")
                    print("  blocks                  - Mostra array de progresso de blocos locais.")
                    print("  get <chunk_id> <porta>  - Requisita manualmente um chunk de um vizinho.")
                    print("  download                - Inicia a transferência P2P automática.")
                    print("  load_metadata <caminho> - Carrega arquivo JSON de metadados de arquivo.")
                    print("  exit / quit             - Encerra o nó com segurança.")

                elif cmd == "load_metadata":
                    if len(parts) < 2:
                        print("[Erro] Sintaxe incorreta. Use: load_metadata <caminho_do_json>")
                        continue
                    path = parts[1]
                    if not os.path.exists(path):
                        print(f"[Erro] Arquivo não encontrado: {path}")
                        continue
                    try:
                        import json
                        with open(path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        self.peer.load_metadata(metadata)
                        downloaded = sum(self.peer.blocks_present)
                        print(f"[Leecher] Metadados de '{metadata['original_name']}' carregados com sucesso.")
                        print(f"[Leecher] Chunks válidos detectados localmente: {downloaded}/{metadata['num_blocks']}")
                    except Exception as e:
                        print(f"[Erro] Erro ao carregar metadados: {e}")

                elif cmd == "get":
                    if len(parts) < 3:
                        print("[Erro] Sintaxe incorreta. Use: get <chunk_id> <porta>")
                        continue

                    chunk_id = parts[1]
                    try:
                        target_port = int(parts[2])
                    except ValueError:
                        print("[Erro] A porta precisa ser um número inteiro válido.")
                        continue

                    try:
                        chunk_id_int = int(chunk_id)
                    except ValueError:
                        print("[Erro] O chunk_id precisa ser um número inteiro válido.")
                        continue

                    self.peer.download_chunk_manually(target_port=target_port, chunk_id=chunk_id_int)

                elif cmd == "download":
                    if self.peer.metadata is None or self.peer.blocks_present is None:
                        print("[Erro] Carregue um metadado com '--metadata' ou 'load_metadata' antes de iniciar o download.")
                        continue
                    self.peer.run_automatic_download(progress_callback=self.show_blocks_progress)

                else:
                    print(f"[Erro] Comando desconhecido: '{cmd}'. Digite 'help' para ajuda.")

        except KeyboardInterrupt:
            print("\n\n[Peer CLI] Interrupção por teclado detectada. Encerrando nó P2P local...")

        finally:
            if self.peer is not None:
                self.peer.stop()
            print("[Peer CLI] Recursos de rede liberados. Até logo!\n")
