import os
import hashlib
import json

class FileMetadata:
    """Gerencia os metadados de arquivos para a rede P2P em memória.

    Esta classe é responsável por ler um arquivo físico do disco, calcular hashes
    SHA-256 de blocos virtuais de tamanho fixo (sem fragmentá-los fisicamente) e extrair
    os metadados necessários para mapeamento na rede P2P.
    """

    def __init__(self, file_path, chunk_size):
        """Inicializa a estrutura de metadados do arquivo.

        Args:
            file_path (str): Caminho local do arquivo original.
            chunk_size (int): Tamanho de cada bloco virtual em bytes.
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.original_name = os.path.basename(file_path) if file_path else ""
        self.total_size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        self.num_blocks = 0
        self.block_hashes = []
        self.file_hash = ""

    def process_file(self):
        """Processa o arquivo de origem gerando hashes de blocos e o hash global.

        Raises:
            FileNotFoundError: Se o arquivo original não for encontrado no caminho especificado.
        """
        if not self.file_path or not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Arquivo original não encontrado: {self.file_path}")

        full_hash = hashlib.sha256()
        self.block_hashes = []

        with open(self.file_path, 'rb') as f:
            chunk_num = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                full_hash.update(chunk)
                chunk_hash = hashlib.sha256(chunk).hexdigest()
                self.block_hashes.append(chunk_hash)
                chunk_num += 1

        self.num_blocks = chunk_num
        self.file_hash = full_hash.hexdigest()

    def to_dict(self):
        """Converte a estrutura de metadados para um dicionário Python.

        Returns:
            dict: Dicionário contendo nome do arquivo, tamanho, tamanho de bloco,
                quantidade de blocos, hash global e lista de hashes de blocos.
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
        """Salva a representação de metadados em um arquivo estruturado JSON.

        Args:
            json_path (str): Caminho físico de saída onde o JSON será persistido.
        """
        parent_dir = os.path.dirname(json_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"Metadados salvos em: {json_path}")

    @staticmethod
    def reconstruct_file(output_file_path, chunks_dict, metadata):
        """Reconstrói o arquivo original em disco a partir dos blocos em memória.

        Args:
            output_file_path (str): Caminho final de gravação do arquivo reconstruído.
            chunks_dict (dict): Dicionário contendo os blocos binários (id -> bytes).
            metadata (dict): Metadados estruturados do arquivo original.

        Returns:
            tuple[bool, str]: Tupla contendo o status de sucesso e mensagem explicativa.
        """
        if metadata is None:
            return False, "[Erro] Nenhum metadado carregado."

        original_name = metadata["original_name"]
        num_blocks = metadata["num_blocks"]

        parent_dir = os.path.dirname(output_file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        print(f"[FileMetadata] Salvando e remontando arquivo final em: {output_file_path}")
        try:
            with open(output_file_path, 'wb') as out_f:
                for i in range(num_blocks):
                    if i not in chunks_dict:
                        return False, f"[Erro] Falha ao reconstruir: Chunk {i} está ausente na memória!"
                    out_f.write(chunks_dict[i])

            full_hash = hashlib.sha256()
            with open(output_file_path, 'rb') as out_f:
                while True:
                    chunk = out_f.read(1024 * 1024)
                    if not chunk:
                        break
                    full_hash.update(chunk)

            reconstructed_hash = full_hash.hexdigest()
            if reconstructed_hash == metadata["file_hash"]:
                msg = f"[Sucesso] Arquivo '{original_name}' reconstruído com sucesso! Hash global validado."
                return True, msg
            else:
                msg = f"[Erro] Falha na validação do arquivo reconstruído!\n -> Esperado: {metadata['file_hash']}\n -> Obtido: {reconstructed_hash}"
                return False, msg
        except Exception as e:
            return False, f"[Erro] Falha ao reconstruir arquivo: {e}"
