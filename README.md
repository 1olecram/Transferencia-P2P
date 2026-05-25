# Transferência de Arquivos P2P

Este projeto consiste na implementação de um sistema elementar de transferência de arquivos utilizando o modelo Peer-to-Peer (P2P). O objetivo é que cada par (Peer) possa atuar simultaneamente como cliente e servidor, fragmentando um arquivo de origem e transferindo seus pedaços diretamente para outro par que o solicita.

---

## 🛠️ Tecnologias e Recursos Utilizados

O projeto foi construído utilizando **Python 3** e depende estritamente de bibliotecas nativas de baixo nível do ecossistema Python, não sendo necessária a instalação de nenhuma dependência de terceiros:

*   **`socket`**: Utilizado para gerenciar a comunicação de rede de baixo nível, operando sobre sockets TCP. A transferência de dados implementa **conexões persistentes**, onde um Leecher estabelece uma única sessão com o Seeder para transferir múltiplos blocos em lote, otimizando drasticamente a vazão e prevenindo a exaustão de portas efêmeras no sistema operacional.
*   **`threading`**: Utilizado para gerenciar a concorrência paralela do nó P2P. Uma thread dedica-se a escutar conexões de entrada na porta TCP designada, enquanto novas conexões de clientes são respondidas paralelamente de forma assíncrona, garantindo que o Peer possa servir chunks enquanto baixa outros concorrentemente.
*   **`hashlib`**: Utilizado para calcular hashes SHA-256 para cada bloco virtual de dados e validar a integridade final do arquivo remontado contra o hash global gerado no Seeder inicial.
*   **`json`**: Utilizado para serialização e persistência de metadados estruturados de compartilhamento de arquivos.
*   **`argparse`**: Utilizado para realizar o parsing de argumentos passados via terminal na inicialização dos nós.
*   **`os` / `sys` / `time`**: Utilizados para manipulação de arquivos do sistema operacional, controle de buffers binários na memória e temporização de tentativas.

---

## 🚀 Como Executar e Testar Manualmente

Para simular o funcionamento da rede distribuída P2P de forma manual, usaremos múltiplos terminais na mesma máquina local (localhost) apontando portas vizinhas estáticas.

O projeto possui um conjunto de arquivos pré-gerados dentro do diretório `base_files/` correspondentes aos cenários de testes sugeridos no trabalho.

### Passo 1: Iniciar o Seeder (Nó com o arquivo original)
O Seeder lê o arquivo binário original sob demanda e disponibiliza seus blocos aos vizinhos na porta estipulada, criando também o arquivo de metadados em formato JSON.

Abra o primeiro terminal e execute:
```bash
# Executa o nó na porta 5001, tendo como vizinho a porta 5002
python3 main.py 5001 5002 -f base_files/file_A.bin
```
*   **`5001`**: A porta local do Seeder.
*   **`5002`**: A porta do vizinho configurada de forma estática.
*   **`-f base_files/file_A.bin`**: Caminho do arquivo original compartilhado.

> [!TIP]
> **Ajuste de Tamanho do Bloco:** Você pode ajustar manualmente o tamanho de fragmentação dos blocos virtuais passando a flag `--block-size` ou `-s` seguida do valor em bytes (por padrão é `1024` ou 1 KB). Exemplo para 4 KB:
> ```bash
> python3 main.py 5001 5002 -f base_files/file_A.bin -s 4096
> ```

---

### Passo 2: Iniciar o Leecher (Nó receptor)
Abra um segundo terminal. O Leecher precisa carregar os metadados JSON gerados pelo Seeder inicial para saber como remontar e validar o arquivo. Esse arquivo de metadados foi salvo na pasta do Seeder (`parts_5001`).

Execute o Leecher no segundo terminal:
```bash
# Executa o Leecher na porta 5002, apontando para o Seeder 5001 e usando seus metadados
python3 main.py 5002 5001 -m parts_5001/file_A.bin_metadata.json
```
*   **`5002`**: A porta local do Leecher.
*   **`5001`**: A porta do vizinho (Seeder).
*   **`-m parts_5001/...`**: O caminho do arquivo JSON de metadados estruturados.

---

### Passo 3: Interagindo com a CLI (Terminal Interativo)
Ao iniciar um Leecher ou Seeder, você terá acesso a um terminal interativo com comandos integrados para controle manual:

*   `status`                  - Testa conexões TCP com os vizinhos pré-configurados e exibe o estado (Online / Offline).
*   `blocks`                  - Exibe visualmente o progresso dos blocos em memória (`[x]` se presente, `[ ]` se ausente).
*   `get <chunk_id> <porta>`  - Requisita manualmente um único chunk binário de uma porta específica e valida seu hash SHA-256.
*   `download`                - Inicia a transferência P2P automática de alta velocidade usando a conexão persistente para baixar e validar sequencialmente todos os chunks ausentes de vizinhos online.
*   `load_metadata <caminho>` - Carrega um novo arquivo de metadados estruturados JSON para preparar o Peer local.
*   `help`                    - Exibe a lista de comandos e explicações.
*   `exit` ou `quit`          - Encerra o nó com segurança, fechando sockets de rede abertos e liberando recursos.

---

### 👥 Cenário de Teste com 4 Peers (Topologia Estática Completa)
Você pode rodar topologias mais complexas abrindo mais terminais. Para simular 4 Peers, iniciamos cada um conhecendo todas as portas dos demais vizinhos:

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

Uma vez ativos, digite `download` nos terminais dos leechers. À medida que eles baixam e validam seus respectivos chunks, eles se tornam seeders temporários em tempo real para os outros nós concorrentes.
