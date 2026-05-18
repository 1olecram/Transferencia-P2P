import os
import hashlib
import json

class FileMetadata:
    """
    Classe responsável por processar um arquivo, dividi-lo em blocos (chunks)
    e extrair metadados para uma rede P2P.
    """
    def __init__(self, file_path, chunk_size):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.original_name = os.path.basename(file_path)
        self.total_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        self.num_blocks = 0
        self.block_hashes = []
        self.file_hash = ""

    def process_file(self, output_dir='parts'):
        """
        Lê o arquivo, divide em blocos, calcula os hashes individuais de cada bloco
        e o hash global do arquivo.
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
        """
        Retorna a estrutura de metadados em formato de dicionário.
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
        """
        Salva os metadados em um arquivo JSON para que o Leecher saiba o que pedir.
        """
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4)
        print(f"Metadados salvos em: {json_path}")
