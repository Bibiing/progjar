import os

def generate_file(directory, filename, size_in_mb):
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    
    size_in_bytes = size_in_mb * 1024 * 1024
    
    with open(filepath, 'wb') as f:
        f.write(os.urandom(size_in_bytes))
    
    print(f"{filepath} ({size_in_mb}MB) berhasil dibuat.")

generate_file("files", "file_10mb.bin", 10)
generate_file("files", "file_50mb.bin", 50)
generate_file("files", "file_100mb.bin", 100)
