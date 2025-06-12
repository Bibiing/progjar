import sys
import os.path
import uuid
from glob import glob
from datetime import datetime

class HttpServer:
    def __init__(self):
        self.sessions={}
        self.types={}
        self.types['.pdf']='application/pdf'
        self.types['.jpg']='image/jpeg'
        self.types['.txt']='text/plain'
        self.types['.html']='text/html'
        
    def response(self,kode=404,message='Not Found',messagebody=bytes(),headers={}):
        tanggal = datetime.now().strftime('%c')
        resp=[]
        resp.append("HTTP/1.0 {} {}\r\n" . format(kode,message))
        resp.append("Date: {}\r\n" . format(tanggal))
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append("Content-Length: {}\r\n" . format(len(messagebody)))
        
        for kk in headers:
            resp.append("{}:{}\r\n" . format(kk,headers[kk]))
        resp.append("\r\n")
        
        response_headers=''
        for i in resp:
            response_headers="{}{}" . format(response_headers,i)
    	#menggabungkan resp menjadi satu string dan menggabungkan dengan messagebody yang berupa bytes
		#response harus berupa bytes
		#message body harus diubah dulu menjadi bytes

        if (type(messagebody) is not bytes):
            messagebody = messagebody.encode()
        
        response = response_headers.encode() + messagebody
		#response adalah bytes
        return response
        
    def proses(self,data):
        requests = data.split("\r\n")
        #print(requests)
        
        baris = requests[0]
        #print(baris)
        
        all_headers = [n for n in requests[1:] if n!='']
        
        j = baris.split(" ")
        try:
            method=j[0].upper().strip()
            if (method=='GET'):
                object_address = j[1].strip()
                return self.http_get(object_address, all_headers)
            if (method=='POST'):
                object_address = j[1].strip()
                # Dapatkan body dari request
                body_start_index = data.find('\r\n\r\n') + 4
                body = data[body_start_index:]
                return self.http_post(object_address, all_headers, body)
            if (method=='DELETE'):
                object_address = j[1].strip()
                return self.http_delete(object_address, all_headers)
            else:
                return self.response(400,'Bad Request','',{})
        except IndexError:
            return self.response(400,'Bad Request','',{})
    
    def http_get(self,object_address,headers):
        thedir='./'
		# Cek jika object_address adalah sebuah direktori
        if object_address.endswith('/'):
            try:
				# Pastikan path aman dan ada
                safe_path = os.path.normpath(os.path.join(thedir, object_address.lstrip('/')))
                if os.path.isdir(safe_path):
					# Dapatkan daftar file dan direktori
                    items = os.listdir(safe_path)
                    html_content = (
                        "<html><body>"
                        "<h1>Directory Listing for {path}</h1>"
                        "<ul>"
                        "{items}"
                        "</ul>"
                        "</body></html>"
                    ).format(
                        path=object_address,
                        items="".join(
                            f"<li><a href='{object_address}{item}'>{item}</a></li>"
                            for item in items
                        )
                    )
                    return self.response(200, 'OK', html_content, {'Content-Type': 'text/html'})
            except OSError:
                return self.response(404, 'Not Found', 'Directory not found.', {})
        
        if (object_address == '/'):
            return self.response(200,'OK','Ini Adalah web Server percobaan',dict())
        if (object_address == '/video'):
            return self.response(302,'Found','',dict(location='https://youtu.be/katoxpnTf04'))
        if (object_address == '/santai'):
            return self.response(200,'OK','santai saja',dict())
        
        local_path = object_address.lstrip('/')
        full_path = os.path.join(thedir, local_path)

        # Cek keberadaan file
        if not os.path.isfile(full_path):
            return self.response(404, 'Not Found', '', {})
            
        # Baca file sebagai binary
        with open(full_path, 'rb') as fp:
            isi = fp.read()
        
        # Tentukan content type berdasarkan ekstensi
        fext = os.path.splitext(full_path)[1]
        content_type = self.types.get(fext, 'application/octet-stream')
        return self.response(200, 'OK', isi, {'Content-Type': content_type})
        
    def http_post(self,object_address,headers,body):
		# Cek jika permintaan adalah untuk upload file
        if object_address == '/upload':
            # Asumsikan nama file ada di header, atau buat nama unik
            content_disposition = next((h for h in headers if h.startswith('Content-Disposition')), None)
            if content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                filename = 'upload_' + str(uuid.uuid4())
		
            # Simpan file yang di-upload
            with open(filename, 'wb') as f:
                f.write(body.encode()) # Pastikan body adalah bytes
            
            return self.response(201, 'Created', f'File {filename} uploaded sukses.', {})
		
		# Logika POST yang sudah ada
        headers ={}
        isi = "kosong"
        return self.response(200,'OK',isi,headers)
    
    def http_delete(self, object_address, headers):
		# Hapus file yang diminta
        filepath = '.' + object_address
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                os.remove(filepath)
                return self.response(200, 'OK', f'File {object_address} deleted.', {})
            except OSError as e:
                return self.response(500, 'Internal Server Error', f'Error menghapus file: {e}', {})
            else:
                return self.response(404, 'Not Found', 'File not found.', {})

if __name__=="__main__":
	httpserver = HttpServer()
	d = httpserver.proses('GET testing.txt HTTP/1.0')
	print(d)
	# d = httpserver.proses('GET donalbebek.jpg HTTP/1.0')
	# print(d)

	# 1. Melihat daftar direktori 
	d = httpserver.proses('GET /certs/ HTTP/1.0')
	print(d)

	# 2. Mengupload file
	file_content_to_upload = "Haloowwww"
	headers_for_upload = ['Content-Disposition: form-data; name="file"; filename="newfile.txt"']
	request_upload = f'POST /upload HTTP/1.0\r\n'
	for h in headers_for_upload:
		request_upload += f'{h}\r\n'
	request_upload += f'\r\n{file_content_to_upload}'
	d = httpserver.proses(request_upload)
	print(d)

	# 3. Menghapus file
	d = httpserver.proses('DELETE /newfile.txt HTTP/1.0')
	print(d)   