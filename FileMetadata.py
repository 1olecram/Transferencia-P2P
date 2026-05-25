import os
import hashlib
import json

class FileMetadata:
    """Gerencia a fragmentação de arquivos e extração de metadados para uma rede P2P.

    Esta classe é responsável por ler um arquivo físico do disco, dividi-lo em
    blocos (chunks) de tamanho fixo, salvar fisicamente cada bloco e extrair os
    metadados necessários (hashes SHA-256 e tamanhos). Esses metadados servem como
    um "mapa" que permite a outros Peers (Leechers) localizarem, solicitarem e
    validarem a integridade de cada segmento do arquivo.

    Attributes:
        file_path (str): Caminho local do arquivo original a ser compartilhado.
        chunk_size (int): Tamanho de cada bloco (chunk) em bytes.
        original_name (str): Nome base do arquivo original.
        total_size (int): Tamanho total do arquivo original em bytes.
        num_blocks (int): Quantidade total de blocos gerados a partir do arquivo.
        block_hashes (list[str]): Lista contendo os hashes SHA-256 de cada bloco em ordem.
        file_hash (str): Hash SHA-256 global correspondente ao arquivo completo.
    """
    def __init__(self, file_path, chunk_size):
        """Inicializa a estrutura de metadados do arquivo.

        Configura os atributos básicos do arquivo, determinando seu tamanho total e
        nome original no disco a partir do caminho fornecido.

        Args:
            file_path (str): O caminho do arquivo a ser processado no sistema de arquivos.
            chunk_size (int): O tamanho desejado em bytes para cada bloco (chunk).
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.original_name = os.path.basename(file_path)
        self.total_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        self.num_blocks = 0
        self.block_hashes = []
        self.file_hash = ""

    def process_file(self, output_dir='parts'):
        """Processa o arquivo de origem fragmentando-o em blocos e calculando os hashes.

        Lê o arquivo original de forma segmentada (em blocos de tamanho chunk_size),
        salva fisicamente cada segmento como um novo arquivo individual no diretório
        especificado, calcula o hash SHA-256 de cada bloco para popular a lista interna
        e constrói o hash global do arquivo.

        Args:
            output_dir (str, optional): O diretório onde os blocos resultantes serão
                salvos no disco. Padrão é 'parts'.

        Raises:
            FileNotFoundError: Se o arquivo original em `self.file_path` não for encontrado.
            IOError: Se ocorrer erro na leitura do arquivo ou na gravação dos blocos.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        full_hash = hashlib.sha256()
            
        with open(self.file_path, 'rb') as f:
            chunk_num = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                # Atualiza o hash global com o bloco atual
                full_hash.update(chunk)
                
                # Salva o bloco no diretório de saída
                chunk_path = os.path.join(output_dir, f'chunk_{chunk_num}')
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk)
                print(f"Salvo: {chunk_path}")
                
                # Calcula o hash SHA-256 do bloco e adiciona à lista
                chunk_hash = hashlib.sha256(chunk).hexdigest()
                self.block_hashes.append(chunk_hash)
                
                chunk_num += 1
                
        self.num_blocks = chunk_num
        self.file_hash = full_hash.hexdigest()
        
    def to_dict(self):
        """Converte a estrutura de metadados para um dicionário Python.

        Esta conversão é um passo intermediário para facilitar a serialização do
        estado atual dos metadados para transporte ou gravação estruturada.

        Returns:
            dict: Um dicionário contendo as seguintes chaves de metadados:
                - original_name (str): Nome do arquivo original.
                - total_size (int): Tamanho total em bytes.
                - chunk_size (int): Tamanho de cada bloco em bytes.
                - num_blocks (int): Quantidade total de blocos.
                - file_hash (str): Hash completo do arquivo original.
                - block_hashes (list[str]): Lista de hashes ordenados de cada bloco.
        """
        return {
            "original_name": self.original_name,
            "total_size": self.total_size,
            "chunk_size": self.chunk_size,
            "num_blocks": self.num_blocks,
            "file_hash": self.file_hash,
            "block_hashes": self.block_hashes
        }
        
    def save_to_json(self, json_path):
        """Salva a representação dos metadados em um arquivo estruturado JSON.

        Grava o dicionário de metadados em um arquivo físico em formato JSON.
        Esse arquivo gerado funciona como a descrição estrutural que outros Peers
        (Leechers) utilizarão para saber quais blocos solicitar e como validar
        cada pedaço recebido.

        Args:
            json_path (str): O caminho do arquivo JSON de saída onde os metadados
                serão persistidos.

        Raises:
            IOError: Se houver erro durante a criação ou escrita no arquivo JSON.
        """
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"Metadados salvos em: {json_path}")

    @staticmethod
    def reconstruct_file(storage_dir, metadata):
        """Reconstrói o arquivo original a partir dos chunks salvos e valida o hash global.

        Args:
            storage_dir (str): Diretório físico onde os chunks estão salvos.
            metadata (dict): Dicionário de metadados do arquivo.

        Returns:
            tuple[bool, str]: Uma tupla (sucesso, mensagem de status/erro).
        """
        if metadata is None:
            return False, "[Erro] Nenhum metadado carregado."

        original_name = metadata["original_name"]
        num_blocks = metadata["num_blocks"]
        output_file_path = os.path.join(storage_dir, original_name)

        print(f"\n[FileMetadata] Reconstrói arquivo original em: {output_file_path}")
        try:
            with open(output_file_path, 'wb') as out_f:
                for i in range(num_blocks):
                    chunk_path = os.path.join(storage_dir, f"chunk_{i}")
                    if not os.path.exists(chunk_path):
                        return False, f"[Erro] Falha ao reconstruir: Chunk {i} está faltando!"
                    with open(chunk_path, 'rb') as chunk_f:
                        out_f.write(chunk_f.read())

            # Valida hash global do arquivo reconstruído
            full_hash = hashlib.sha256()
            with open(output_file_path, 'rb') as out_f:
                while True:
                    chunk = out_f.read(1024 * 1024)
                    if not chunk:
                        break
                    full_hash.update(chunk)

            reconstructed_hash = full_hash.hexdigest()
            if reconstructed_hash == metadata["file_hash"]:
                msg = f"[Sucesso] Arquivo '{original_name}' reconstruído com sucesso!\n -> Hash global validado: {reconstructed_hash}"
                return True, msg
            else:
                msg = f"[Erro] Falha na validação do arquivo reconstruído!\n -> Esperado: {metadata['file_hash']}\n -> Obtido: {reconstructed_hash}"
                return False, msg
        except Exception as e:
            return False, f"[Erro] Falha ao reconstruir arquivo: {e}"

