import os
import json
import base64
from glob import glob


class FileInterface:
    def __init__(self):
        if not os.path.exists('files/'):
            os.makedirs('files/')
        os.chdir('files/')

    def list(self,params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK',data=filelist)
        except Exception as e:
            return dict(status='ERROR',data=str(e))

    def get(self, params=[]):
        try:
            if not params or params[0] == '':
                return dict(status='ERROR', data='Nama file tidak boleh kosong')
            
            filename = params[0]
            
            # Cek apakah file ada
            if not os.path.exists(filename):
                return dict(status='ERROR', data=f'File {filename} tidak ditemukan')
            
            with open(filename, 'rb') as fp:
                file_content = fp.read()
            
            # Encode ke base64
            isi_file_base64 = base64.b64encode(file_content).decode()
            
            return dict(
                status='OK',
                data_namafile=filename,
                data_file=isi_file_base64
            )
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def upload(self, params=[]):
        """Upload file ke server"""
        try:
            if len(params) < 2:
                return dict(status='ERROR', data='Parameter tidak lengkap. Dibutuhkan: nama_file dan content_base64')
            
            filename = params[0]
            content_base64 = params[1]
            
            # Validasi nama file
            if filename == '':
                return dict(status='ERROR', data='Nama file tidak boleh kosong')
            
            # Decode content dari base64
            try:
                file_content = base64.b64decode(content_base64)
            except Exception as e:
                return dict(status='ERROR', data=f'Error decoding base64: {str(e)}')
            
            # Simpan file
            with open(filename, 'wb') as f:
                f.write(file_content)
            
            return dict(status='OK', data=f'{filename} uploaded successfully')
            
        except Exception as e:
            return dict(status='ERROR', data=str(e))

    def delete(self, params=[]):
        try:
            if not params or params[0] == '':
                return dict(status='ERROR', data='Nama file tidak boleh kosong')
            
            filename = params[0]
            
            # Cek apakah file ada
            if not os.path.exists(filename):
                return dict(status='ERROR', data=f'File {filename} tidak ditemukan')
            
            # Hapus file
            os.remove(filename)
            
            return dict(status='OK', data=f'{filename} deleted successfully')
            
        except Exception as e:
            return dict(status='ERROR', data=str(e))



if __name__=='__main__':
    f = FileInterface()
    print(f.list())
    print(f.get(['pokijan.jpg']))