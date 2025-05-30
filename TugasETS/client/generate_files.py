import os
import base64

def generate_b64_file(directory, filename, size_in_mb):
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    
    size_in_bytes = size_in_mb * 1024 * 1024
    
    # 1. Buat data biner acak
    random_binary_data = os.urandom(size_in_bytes)
    
    # 2. Encode data biner tersebut ke Base64
    encoded_data = base64.b64encode(random_binary_data)
    
    # 3. Simpan data yang sudah di-encode ke dalam file
    with open(filepath, 'wb') as f:
        f.write(encoded_data)
        
    print(f"File Base64 '{filepath}' ({size_in_mb}MB data asli) berhasil dibuat.")

generate_b64_file("doc", "file_10mb.txt", 10)
generate_b64_file("doc", "file_50mb.txt", 50)
generate_b64_file("doc", "file_100mb.txt", 100)