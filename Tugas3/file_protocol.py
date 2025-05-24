import json
import logging
import shlex

from file_interface import FileInterface

"""
* class FileProtocol bertugas untuk memproses 
data yang masuk, dan menerjemahkannya apakah sesuai dengan
protokol/aturan yang dibuat

* data yang masuk dari client adalah dalam bentuk bytes yang 
pada akhirnya akan diproses dalam bentuk string

* class FileProtocol akan memproses data yang masuk dalam bentuk
string
"""



class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
        
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def proses_string(self, string_datamasuk=''):
        logging.warning(f"String diproses: {string_datamasuk}")
        
        try:
            # Parse command menggunakan shlex untuk handle quoted strings
            parsed_command = shlex.split(string_datamasuk)
            
            if not parsed_command:
                return json.dumps(dict(status='ERROR', data='Command kosong'))
            
            command = parsed_command[0].strip().lower()
            params = [x for x in parsed_command[1:]]
            
            logging.warning(f"Memproses request: {command} dengan parameter: {params}")
            
            supported_commands = ['list', 'get', 'upload', 'delete']
            if command not in supported_commands:
                return json.dumps(dict(
                    status='ERROR', 
                    data=f'Request tidak dikenali. Command yang didukung: {", ".join(supported_commands)}'
                ))
            
            if hasattr(self.file, command):
                result = getattr(self.file, command)(params)
                return json.dumps(result)
            else:
                return json.dumps(dict(status='ERROR', data='Command tidak tersedia'))
                
        except Exception as e:
            logging.error(f"Error processing command: {str(e)}")
            return json.dumps(dict(status='ERROR', data=f'Error processing command: {str(e)}'))

if __name__=='__main__':
    #contoh pemakaian
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET pokijan.jpg"))
