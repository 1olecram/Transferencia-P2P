import os

def split_file(file_path, size, output_dir='parts'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    with open(file_path, 'rb') as f:
        chunk_num = 0
        while True:
            chunk = f.read(size)
            if not chunk:
                break
            
            chunk_path = os.path.join(output_dir, f'chunk_{chunk_num}')
            with open(chunk_path, 'wb') as chunk_file:
                chunk_file.write(chunk)
            print(f"Salvo: {chunk_path}")
            
            chunk_num += 1

def main():
    size = 1024 # 1kb
    split_file('base_files/file_A.bin', size)

if __name__ == "__main__":
    main()
