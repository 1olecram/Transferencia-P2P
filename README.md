# Transferência de Arquivos P2P

Este projeto consiste na implementação de um sistema elementar de transferência de arquivos utilizando o modelo Peer-to-Peer (P2P). O objetivo é que cada par (Peer) possa atuar simultaneamente como cliente e servidor, fragmentando um arquivo de origem e transferindo seus pedaços diretamente para outro par que o solicita.

---

## 🛠️ Tecnologias Utilizadas

*   **Linguagem:** Python 3.x
*   **Bibliotecas Nativas:** `socket` (rede), `threading` (concorrência paralela), `hashlib` (checksum SHA-256), `json` (metadados).

---

## 📂 Geração dos Arquivos de Teste

Para cumprir os parâmetros de configuração base e simular um ambiente de rede real, os arquivos de teste foram gerados utilizando o utilitário nativo do Linux `dd`. 

Esta abordagem garante a criação de arquivos binários com tamanhos precisos e conteúdo aleatório (entropia alta) único, o que é essencial para validar de forma confiável a integridade da transferência via algoritmo SHA-256.

Para preparar o seu ambiente, você pode utilizar os seguintes comandos no terminal:

```bash
# Arquivos de Teste Padrão
dd if=/dev/urandom of=file_A.bin bs=1K count=10   # Arquivo Pequeno (10 KB)
dd if=/dev/urandom of=file_B.bin bs=1M count=1    # Arquivo Médio (1 MB)
dd if=/dev/urandom of=file_C.bin bs=1M count=10   # Arquivo Grande (10 MB)

# Arquivos de Teste Variáveis
dd if=/dev/urandom of=file_Avt.bin bs=1K count=20 # Arquivo Pequeno Variável (20 KB)
dd if=/dev/urandom of=file_Bvt.bin bs=1M count=5  # Arquivo Médio Variável (5 MB)
dd if=/dev/urandom of=file_Cvt.bin bs=1M count=20 # Arquivo Grande Variável (20 MB)
```

## 🚀 Como Executar e Testar

Para testar o sistema, utilizaremos múltiplas instâncias em portas locais simulando a rede P2P.

### Passo 1: Iniciar o Seeder (Nó com o arquivo original)
O Seeder irá ler o arquivo original, dividi-lo em pedaços e criar o arquivo JSON de metadados.

```bash
# Executa o nó na porta 5001, tendo como vizinhos as portas 5002 e 5003
python3 main.py 5001 5002 5003 -f base_files/file_A.bin
```
*(Opcional) Você pode definir o tamanho do bloco (padrão é 1024 bytes) com a flag `-s` ou `--block-size`:*
```bash
python3 main.py 5001 5002 5003 -f base_files/file_A.bin -s 4096
```

### Passo 2: Iniciar o Leecher (Nó que deseja baixar o arquivo)
Em outro terminal, execute o Leecher passando o caminho do arquivo de metadados gerado na pasta do Seeder (`parts_5001`):

```bash
# Executa o Leecher na porta 5002, com vizinhos 5001 e 5003, apontando para o arquivo de metadados
python3 main.py 5002 5001 5003 -m parts_5001/file_A.bin_metadata.json
```

---

## 💻 Comandos da CLI Interativa

Uma vez inicializado o nó, você terá acesso ao terminal interativo com os seguintes comandos:

*   `status`                  - Testa a conexão TCP e mostra quais vizinhos estão Online/Offline.
*   `blocks`                  - Exibe graficamente quais blocos do arquivo você possui localmente (`[x]` ou `[ ]`).
*   `get <chunk_id> <porta>`  - Baixa e valida manualmente um bloco específico de um vizinho na porta informada.
*   `download`                - Inicia a transferência P2P automatizada e cooperativa dos blocos ausentes.
*   `load_metadata <caminho>` - Carrega um novo arquivo de metadados JSON.
*   `help`                    - Exibe o menu de ajuda com a lista de comandos.
*   `exit` ou `quit`          - Encerra o nó P2P com segurança, fechando todas as conexões.
