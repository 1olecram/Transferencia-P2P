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
O Seeder irá ler o arquivo original, dividi-lo em pedaços e criar o arquivo JSON de metadados. O número de portas de vizinhos passadas pode ser qualquer um (ex: testar com 2, 3, 4 ou mais peers).

```bash
# Executa o nó na porta 5001, tendo como vizinhos as portas 5002 e 5003 (Cenário de 3 Peers)
python3 main.py 5001 5002 5003 -f base_files/file_A.bin

# Ou com a flag opcional de customização do tamanho do bloco (ex: 4096 bytes)
python3 main.py 5001 5002 5003 -f base_files/file_A.bin -s 4096
```

### Passo 2: Iniciar os Leechers (Nós que desejam baixar o arquivo)
Em outros terminais, execute os Leechers passando o caminho do arquivo de metadados gerado na pasta do Seeder (`parts_5001`) e a lista de seus respectivos vizinhos:

```bash
# Executa o Leecher na porta 5002, tendo 5001 e 5003 como vizinhos
python3 main.py 5002 5001 5003 -m parts_5001/file_A.bin_metadata.json
```

---

## 👥 Cenário de Teste com 4 Peers (Múltiplos Vizinhos)

O argumento de vizinhos é dinâmico. Para testar com **4 peers** simultâneos ativos (portas 5001, 5002, 5003 e 5004), cada nó deve ser iniciado especificando todos os outros nós como vizinhos:

```bash
# Terminal 1 - Seeder (porta 5001, vizinhos: 5002, 5003 e 5004)
python3 main.py 5001 5002 5003 5004 -f base_files/file_A.bin

# Terminal 2 - Leecher A (porta 5002, vizinhos: 5001, 5003 e 5004)
python3 main.py 5002 5001 5003 5004 -m parts_5001/file_A.bin_metadata.json

# Terminal 3 - Leecher B (porta 5003, vizinhos: 5001, 5002 e 5004)
python3 main.py 5003 5001 5002 5004 -m parts_5001/file_A.bin_metadata.json

# Terminal 4 - Leecher C (porta 5004, vizinhos: 5001, 5002 e 5003)
python3 main.py 5004 5001 5002 5003 -m parts_5001/file_A.bin_metadata.json
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
