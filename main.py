def read_file(file_path, size):
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(size)
            if not chunk:
                break
            
            print(chunk)

def main():
    size = 1024 
    read_file('base_files/file_A.bin', size)

if __name__ == "__main__":
    main()

