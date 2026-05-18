import os
from FileMetadata import FileMetadata

def main():
    size = 1024 # 1kb
    file_path = 'base_files/file_A.bin'
    
    print(f"Processando arquivo: {file_path}")
    
    # Cria o objeto de metadados
    metadata = FileMetadata(file_path, size)
    
    # Processa o arquivo (lê, divide em partes e calcula os hashes)
    metadata.process_file(output_dir='parts')
    
    # Salva o arquivo .json com a estrutura para os Leechers
    json_path = os.path.join('parts', f'{metadata.original_name}_metadata.json')
    metadata.save_to_json(json_path)

if __name__ == "__main__":
    main()
