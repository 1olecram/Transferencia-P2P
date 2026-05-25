"""Script principal CLI para execução e gerenciamento de um nó P2P (Peer).

Este script atua como o ponto de entrada principal do programa e o "ponto de união"
de toda a arquitetura orientada a objetos. Ele analisa os argumentos da linha de comando,
inicializa e configura os componentes FileMetadata e Peer, e dispara a CLI interativa.
"""

import argparse
import sys
import os
import json
import time
from CLI import CLI
from Peer import Peer
from FileMetadata import FileMetadata


def main():
    """Função principal que analisa argumentos, inicializa e roda o nó P2P com sua CLI."""
    parser = argparse.ArgumentParser(
        description="Inicializa um nó P2P CLI unificado com escuta e sincronização automatizada."
    )
    parser.add_argument(
        'minha_porta',
        type=int,
        help="Porta TCP em que este Peer irá escutar conexões de entrada."
    )
    parser.add_argument(
        'vizinhos',
        type=int,
        nargs='+',
        help="Porta(s) TCP dos nós vizinhos (uma ou mais separadas por espaço)."
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        default=None,
        help="Caminho do arquivo completo para atuar como Seeder (fragmenta e disponibiliza)."
    )
    parser.add_argument(
        '--metadata', '-m',
        type=str,
        default=None,
        help="Caminho do arquivo JSON de metadados para atuar como Leecher."
    )
    parser.add_argument(
        '--block-size', '-s',
        type=int,
        default=1024,
        help="Tamanho de cada bloco (chunk) em bytes para a fragmentação. Padrão é 1024 (1 KB)."
    )

    args = parser.parse_args()
    minha_porta = args.minha_porta
    vizinhos = args.vizinhos

    if minha_porta in vizinhos:
        print(f"[Erro] A porta local ({minha_porta}) não pode ser igual às portas dos vizinhos.")
        sys.exit(1)

    storage_dir = f"parts_{minha_porta}"
    metadata = None
    blocks_present = None

    # Configuração inicial do nó (Seeder vs Leecher)
    if args.file:
        if not os.path.exists(args.file):
            print(f"[Erro] Arquivo original não encontrado: {args.file}")
            sys.exit(1)

        print(f"\n[Seeder] Processando e fragmentando o arquivo: {args.file} (Tamanho do Bloco: {args.block_size} bytes)")
        metadata_obj = FileMetadata(args.file, args.block_size)
        metadata_obj.process_file(output_dir=storage_dir)

        json_path = os.path.join(storage_dir, f"{metadata_obj.original_name}_metadata.json")
        metadata_obj.save_to_json(json_path)

        metadata = metadata_obj.to_dict()
        blocks_present = [True] * metadata["num_blocks"]
        print(f"[Seeder] Inicializado como Seeder com {metadata['num_blocks']} chunks ativos.")

    elif args.metadata:
        if not os.path.exists(args.metadata):
            print(f"[Erro] Metadados não encontrados em: {args.metadata}")
            sys.exit(1)

        try:
            with open(args.metadata, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            print(f"[Leecher] Metadados de '{metadata['original_name']}' carregados.")
        except Exception as e:
            print(f"[Erro] Falha ao ler arquivo de metadados: {e}")
            sys.exit(1)
    else:
        print("\n[Aviso] Iniciando sem arquivo ou metadados associados.")
        print("Digite 'load_metadata <caminho>' na CLI para preparar para download.")

    # Criação do Peer
    peer = Peer(
        port=minha_porta,
        vizinhos=vizinhos,
        storage_dir=storage_dir,
        metadata=metadata,
        blocks_present=blocks_present
    )

    # Inicialização da escuta TCP
    try:
        peer.start_listening()
    except Exception as e:
        print(f"[Erro] Falha ao vincular à porta {minha_porta}: {e}")
        print("Verifique se a porta já está em uso por outro processo.")
        sys.exit(1)

    time.sleep(0.5)

    # Validação inicial de blocos para Leecher
    if args.metadata and peer.metadata:
        peer.validate_and_update_blocks()
        downloaded = sum(peer.blocks_present) if peer.blocks_present else 0
        print(f"[Leecher] Chunks válidos detectados localmente: {downloaded}/{peer.metadata['num_blocks']}")

    # Cria e inicializa a CLI
    cli = CLI(peer=peer)
    cli.run()


if __name__ == "__main__":
    main()
