# 🌐 Transferencia-P2P

> Implementação de um sistema elementar de transferência de arquivos utilizando o modelo Peer-to-Peer (P2P).

O objetivo é que cada par (Peer) possa atuar simultaneamente como cliente e servidor, fragmentando um arquivo de origem e transferindo seus pedaços diretamente para outro par que o solicita.

---

## 🎯 Objetivos

- **Comunicação P2P:** Implementar a comunicação P2P simétrica.
- **Fragmentação:** Realizar a fragmentação e remontagem de arquivos grandes em blocos de tamanho fixo.
- **Concorrência:** Gerenciar conexões bidirecionais simultâneas em um único nó.
- **Integridade:** Garantir a integridade dos dados via Checksum (SHA-256).

---

## 🛠️ Tecnologias e Requisitos

- **Linguagem:** Python 3.x
- **Bibliotecas Principais:** 
  - `socket` (comunicação na rede)
  - `threading` (execução simultânea e concorrência)
  - `hashlib` (garantia de integridade e checksum)
  - `json` (serialização de mensagens e dados)
- **Ambiente:** Testado em ambiente Linux (Zorin OS) utilizando múltiplas instâncias via portas locais.

---

## 🏗️ Arquitetura do Sistema

O sistema opera sem a necessidade obrigatória de um Tracker (servidor central), utilizando uma lista de vizinhos predefinida para formar a rede overlay.

### 🧩 Componentes do Peer

1. **Servidor (Seeder):** Escuta em uma porta específica para atender às solicitações de blocos de outros pares.
2. **Cliente (Leecher):** Conecta-se aos vizinhos configurados para solicitar blocos ausentes que compõem o arquivo desejado.
3. **Fragmentador:** Responsável por dividir o arquivo original em blocos de **1024 Bytes (1 KB)** para otimizar a transferência.
4. **Monitor de Blocos:** Mantém um registro (hash map ou array) dos blocos já possuídos para gerenciar o progresso geral do download e evitar solicitações duplicadas.

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
