import os
import shutil
import time
import hashlib
import threading
from FileMetadata import FileMetadata
from Peer import Peer

# Configuração dos arquivos de teste baseados no diretório base_files
BASE_FILES_DIR = "base_files"
TEST_FILES = {
    "Pequeno (File A - 10KB)": {"path": os.path.join(BASE_FILES_DIR, "file_A.bin"), "size": 10240},
    "Pequeno Variação (File Avt - 20KB)": {"path": os.path.join(BASE_FILES_DIR, "file_Avt.bin"), "size": 20480},
    "Médio (File B - 1MB)": {"path": os.path.join(BASE_FILES_DIR, "file_B.bin"), "size": 1048576},
    "Médio Variação (File Bvt - 5MB)": {"path": os.path.join(BASE_FILES_DIR, "file_Bvt.bin"), "size": 5242880},
    "Grande (File C - 10MB)": {"path": os.path.join(BASE_FILES_DIR, "file_C.bin"), "size": 10485760},
    "Grande Variação (File Cvt - 20MB)": {"path": os.path.join(BASE_FILES_DIR, "file_Cvt.bin"), "size": 20971520},
}

def calculate_file_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def clean_temp_dirs(ports):
    for port in ports:
        path = f"parts_{port}"
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except Exception:
                pass

def run_single_test(test_id, num_peers, block_size, file_info):
    file_label, file_data = file_info
    filepath = file_data["path"]
    filesize = file_data["size"]
    
    print(f"\n==================================================")
    print(f" TESTE {test_id}: {num_peers} Peers | Bloco: {block_size}B | {file_label}")
    print(f"==================================================")
    
    ports = [6000 + test_id * 10 + i for i in range(1, num_peers + 1)]
    clean_temp_dirs(ports)
    
    # 1. Processar metadados do arquivo do Seeder
    meta_obj = FileMetadata(filepath, block_size)
    meta_obj.process_file()
    metadata = meta_obj.to_dict()
    
    original_hash = metadata["file_hash"]
    
    # 2. Instanciar os nós (Peer 5001 é o Seeder inicial, os outros são Leechers)
    peers = []
    
    # Seeder
    seeder_port = ports[0]
    seeder = Peer(
        port=seeder_port,
        vizinhos=ports[1:],
        storage_dir=f"parts_{seeder_port}",
        metadata=metadata,
        original_file_path=filepath
    )
    peers.append(seeder)
    
    # Leechers
    leechers = []
    for port in ports[1:]:
        vizinhos = [p for p in ports if p != port]
        leecher = Peer(
            port=port,
            vizinhos=vizinhos,
            storage_dir=f"parts_{port}",
            metadata=metadata,
            blocks_present=[False] * metadata["num_blocks"]
        )
        peers.append(leecher)
        leechers.append(leecher)
        
    # 3. Iniciar todos os Peers escutando em threads dedicadas
    for p in peers:
        p.start_listening()
        
    # Espera rápida para conexões estabilizarem
    time.sleep(0.1)
    
    # 4. Iniciar downloads nos leechers simultaneamente
    start_time = time.time()
    download_threads = []
    for leecher in leechers:
        t = threading.Thread(target=leecher.run_automatic_download)
        t.start()
        download_threads.append(t)
        
    # Aguarda a conclusão dos downloads
    for t in download_threads:
        t.join()
        
    duration = time.time() - start_time
    
    # 5. Validação dos resultados
    all_success = True
    validated_leechers = 0
    
    for leecher in leechers:
        downloaded_filepath = os.path.join(leecher.storage_dir, metadata["original_name"])
        if os.path.exists(downloaded_filepath):
            downloaded_hash = calculate_file_hash(downloaded_filepath)
            if downloaded_hash == original_hash:
                validated_leechers += 1
            else:
                all_success = False
        else:
            all_success = False
            
    # 6. Desligamento seguro de todos os sockets de escuta
    for p in peers:
        p.stop()
        
    # Tempo para liberação da porta do OS
    time.sleep(0.2)
    
    # Limpa diretórios temporários para poupar espaço
    clean_temp_dirs(ports)
    
    # Cálculo da vazão
    total_data_transferred_mb = (filesize * len(leechers)) / (1024 * 1024)
    vazao = total_data_transferred_mb / duration if duration > 0 else 0
    
    status_str = "SUCESSO" if (all_success and validated_leechers == len(leechers)) else "FALHA"
    
    print(f"\n-> Resultado do Teste {test_id}: {status_str}")
    print(f"-> Tempo decorrido: {duration:.3f} segundos")
    print(f"-> Vazão Total Coletiva: {vazao:.2f} MB/s")
    
    return {
        "id": test_id,
        "peers": num_peers,
        "block_size": block_size,
        "file_label": file_label,
        "filesize_kb": filesize / 1024,
        "duration": duration,
        "vazao": vazao,
        "status": status_str
    }

def main():
    print("=" * 60)
    print(" INICIANDO TESTES DA TABELA 1 - TRANSFERÊNCIA P2P ".center(60, "="))
    print("=" * 60)
    
    # Lista de cenários combinando todos os fatores da Tabela 1
    # Formato: (num_peers, block_size, file_key)
    scenarios = [
        # 1. Testes com 2 Peers, Bloco de 1KB (Valor Padrão)
        (2, 1024, "Pequeno (File A - 10KB)"),
        (2, 1024, "Pequeno Variação (File Avt - 20KB)"),
        (2, 1024, "Médio (File B - 1MB)"),
        (2, 1024, "Médio Variação (File Bvt - 5MB)"),
        (2, 1024, "Grande (File C - 10MB)"),
        (2, 1024, "Grande Variação (File Cvt - 20MB)"),
        
        # 2. Testes com 2 Peers, Bloco de 4KB (Variação de Fragmentação)
        (2, 4096, "Pequeno (File A - 10KB)"),
        (2, 4096, "Pequeno Variação (File Avt - 20KB)"),
        (2, 4096, "Médio (File B - 1MB)"),
        (2, 4096, "Médio Variação (File Bvt - 5MB)"),
        (2, 4096, "Grande (File C - 10MB)"),
        (2, 4096, "Grande Variação (File Cvt - 20MB)"),
        
        # 3. Testes com 4 Peers, Bloco de 1KB (Variação de Peers)
        (4, 1024, "Pequeno (File A - 10KB)"),
        (4, 1024, "Pequeno Variação (File Avt - 20KB)"),
        (4, 1024, "Médio (File B - 1MB)"),
        (4, 1024, "Médio Variação (File Bvt - 5MB)"),
        (4, 1024, "Grande (File C - 10MB)"),
        (4, 1024, "Grande Variação (File Cvt - 20MB)"),
        
        # 4. Testes com 4 Peers, Bloco de 4KB (Variação Total de Peers e Fragmentação)
        (4, 4096, "Pequeno (File A - 10KB)"),
        (4, 4096, "Pequeno Variação (File Avt - 20KB)"),
        (4, 4096, "Médio (File B - 1MB)"),
        (4, 4096, "Médio Variação (File Bvt - 5MB)"),
        (4, 4096, "Grande (File C - 10MB)"),
        (4, 4096, "Grande Variação (File Cvt - 20MB)"),
    ]
    
    results = []
    
    for idx, (peers, block_size, file_key) in enumerate(scenarios, 1):
        file_info = (file_key, TEST_FILES[file_key])
        result = run_single_test(idx, peers, block_size, file_info)
        results.append(result)
        # Dorme um pouco para liberar sockets no sistema operacional
        time.sleep(0.5)
        
    print("\n" + "=" * 80)
    print(" RELATÓRIO FINAL DOS TESTES DA TABELA 1 ".center(80, "="))
    print("=" * 80)
    
    # Montar tabela markdown no console
    markdown_lines = [
        "| ID | Qtd. Peers | Tam. Bloco | Arquivo de Teste | Tamanho (KB) | Tempo (s) | Vazão Total (MB/s) | Status |",
        "|:--:|:----------:|:----------:|:-----------------|:------------:|:---------:|:------------------:|:------:|",
    ]
    
    for r in results:
        line = f"| {r['id']} | {r['peers']} | {r['block_size']} B | {r['file_label']} | {r['filesize_kb']:.1f} KB | {r['duration']:.4f} s | {r['vazao']:.4f} MB/s | {r['status']} |"
        markdown_lines.append(line)
        
    print("\n".join(markdown_lines))
    print("=" * 80 + "\n")
    
    # Salvar resultados em um arquivo Markdown local
    with open("resultado_testes.md", "w", encoding="utf-8") as out_f:
        out_f.write("# Resultados dos Testes P2P - Tabela 1\n\n")
        out_f.write("\n".join(markdown_lines))
        out_f.write("\n")
    print("Resultados salvos em 'resultado_testes.md'")

if __name__ == "__main__":
    main()
