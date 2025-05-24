from socket import *
import socket
import threading
import logging
import time
import sys


from file_protocol import  FileProtocol
fp = FileProtocol()

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)


class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        self.buffer_size = 1060
        threading.Thread.__init__(self)
        self.daemon = True  

    def run(self):
        logging.warning(f"Client {self.address} connected")
        
        try:
            while True:
                # Terima data dari client
                data = self.connection.recv(self.buffer_size)
                
                if not data:
                    # Koneksi ditutup oleh client
                    logging.warning(f"Client {self.address} disconnected")
                    break
                
                # Decode data menjadi string
                try:
                    request_string = data.decode('utf-8').strip()
                    logging.warning(f"Received from {self.address}: {request_string[:100]}...")  # Log first 100 chars
                    
                    # Proses request menggunakan FileProtocol
                    response = fp.proses_string(request_string)
                    
                    # Tambahkan terminator sesuai protokol
                    response_with_terminator = response + "\r\n\r\n"
                    
                    # Kirim response ke client
                    self.connection.sendall(response_with_terminator.encode('utf-8'))
                    
                    logging.warning(f"Response sent to {self.address}: {len(response)} bytes")
                    
                except UnicodeDecodeError as e:
                    # Handle encoding error
                    error_response = '{"status": "ERROR", "data": "Invalid character encoding"}\r\n\r\n'
                    self.connection.sendall(error_response.encode('utf-8'))
                    logging.error(f"Encoding error from {self.address}: {str(e)}")
                
                except Exception as e:
                    # Handle other errors
                    error_response = f'{{"status": "ERROR", "data": "Server error: {str(e)}"}}\r\n\r\n'
                    self.connection.sendall(error_response.encode('utf-8'))
                    logging.error(f"Error processing request from {self.address}: {str(e)}")
                    
        except ConnectionResetError:
            logging.warning(f"Connection reset by client {self.address}")
        except Exception as e:
            logging.error(f"Unexpected error with client {self.address}: {str(e)}")
        finally:
            # Pastikan koneksi ditutup
            try:
                self.connection.close()
                logging.warning(f"Connection to {self.address} closed")
            except:
                pass

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=8889):
        self.ip_info = (ipaddress, port)
        self.the_clients = []
        self.running = True
        
        # Setup socket
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        threading.Thread.__init__(self)
        self.daemon = True


    def run(self):
        try:
            logging.warning(f"Server starting on {self.ip_info[0]}:{self.ip_info[1]}")
            print(f"File Server started on {self.ip_info[0]}:{self.ip_info[1]}")
            print(f"Working directory: files/")
            print("-" * 50)
            
            self.my_socket.bind(self.ip_info)
            self.my_socket.listen(5) 
            
            while self.running:
                try:
                    # Accept new connection
                    connection, client_address = self.my_socket.accept()
                    
                    logging.warning(f"New connection from {client_address}")
                    print(f"Client connected: {client_address}")
                    
                    # Create new thread for this client
                    client_thread = ProcessTheClient(connection, client_address)
                    client_thread.start()
                    
                    # Add to client list (cleanup old threads)
                    self.the_clients.append(client_thread)
                    self.cleanup_clients()
                    
                except socket.error as e:
                    if self.running:  # Only log if we're supposed to be running
                        logging.error(f"Socket error: {str(e)}")
                        
        except KeyboardInterrupt:
            print("\nServer shutdown requested")
            self.stop_server()
        except Exception as e:
            logging.error(f"Server error: {str(e)}")
            print(f"Server error: {str(e)}")
        finally:
            self.cleanup()
            
    def cleanup_clients(self):
        self.the_clients = [client for client in self.the_clients if client.is_alive()]

    def stop_server(self):
        print("Stopping server...")
        self.running = False
        
        # Close main socket
        try:
            self.my_socket.shutdown(socket.SHUT_RDWR)
            self.my_socket.close()
        except:
            pass
        
        # Wait for client threads to finish (with timeout)
        for client in self.the_clients:
            if client.is_alive():
                client.join(timeout=2.0)
        
        print("Server stopped successfully")

    def cleanup(self):
        try:
            if hasattr(self, 'my_socket'):
                self.my_socket.close()
        except:
            pass



def main():
    ip_address = '0.0.0.0'
    port = 8889
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Error: Port must be a number")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        ip_address = sys.argv[2]
    
    try:
        server = Server(ipaddress=ip_address, port=port)
        server.start()
        
        while server.is_alive():
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Failed to start server: {str(e)}")
        logging.error(f"Failed to start server: {str(e)}")


if __name__ == "__main__":
    main()

