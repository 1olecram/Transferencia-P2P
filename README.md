# Transferência de Arquivos P2P

Este projeto consiste na implementação de um sistema elementar de transferência de arquivos utilizando o modelo Peer-to-Peer (P2P). O objetivo é que cada par (Peer) possa atuar simultaneamente como cliente e servidor, fragmentando um arquivo de origem e transferindo seus pedaços diretamente para outro par que o solicita.

---

## 🛠️ Tecnologias Utilizadas

*   **Linguagem:** Python 3.x
*   **Bibliotecas Nativas:** `socket` (rede), `threading` (concorrência paralela), `hashlib` (checksum SHA-256), `json` (metadados).

---

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
