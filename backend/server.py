## Create the server side of the application

# import libraries
import socket
import threading
import os
import hashlib

# create server as class
class FileServer:
    # Constructor
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # to track active clients

    # Function to start server
    def start_server(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")

        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"New connection from {client_address}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()
    
    # Function to handle client
    def handle_client(self, client_socket):
        authenticated = self.authenticate(client_socket)
        if not authenticated:
            client_socket.close()
            return
        
        while True:
            try:
                request = client_socket.recv(1024).decode()
                if not request:
                    break
                command, *args = request.split()
                self.process_command(client_socket, command, args)
            except Exception as e:
                print(f"Error: {e}")
                client_socket.send(b"An error occurred.")
                break

        client_socket.close()
    
    def authenticate(self, client_socket):
        """Basic authentication: Ask for username and password."""
        client_socket.send(b"Username: ")
        username = client_socket.recv(1024).decode().strip()
        client_socket.send(b"Password: ")
        password = client_socket.recv(1024).decode().strip()

        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Check credentials
        if username == "user" and password_hash == hashlib.sha256(b"pass").hexdigest():
            client_socket.send(b"Authentication successful.\n")
            return True
        else:
            client_socket.send(b"Authentication failed.\n")
            return False
    
    # Function to process commands
    def process_command(self, client_socket, command, args):
        if command == "UPLOAD":
            self.upload_file(client_socket, args[0])
        elif command == "DOWNLOAD":
            self.download_file(client_socket, args[0])
        elif command == "DELETE":
            self.delete_file(client_socket, args[0])
        elif command == "DIR":
            self.list_files(client_socket)
        else:
            client_socket.send(b"Invalid command.\n")
    
    # Function to upload file
    def upload_file(self, client_socket, filename):
        """Handles file upload from client."""
        filepath = os.path.join("server_storage", filename)
        if os.path.exists(filepath):
            client_socket.send(b"File exists. Overwrite? (y/n): ")
            response = client_socket.recv(1024).decode().strip().lower()
            if response != 'y':
                client_socket.send(b"Upload cancelled.\n")
                return
        
        client_socket.send(b"Ready to receive file.\n")
        with open(filepath, 'wb') as f:
            while True:
                data = client_socket.recv(1024)
                if data == b"EOF":
                    break
                f.write(data)
        client_socket.send(b"File uploaded successfully.\n")

    # Function to download file
    def download_file(self, client_socket, filename):
        """Handles file download to client."""
        filepath = os.path.join("server_storage", filename)
        if not os.path.exists(filepath):
            client_socket.send(b"File not found.\n")
            return
        
        client_socket.send(b"Ready to send file.\n")
        with open(filepath, 'rb') as f:
            while chunk := f.read(1024):
                client_socket.send(chunk)
        client_socket.send(b"EOF")
        client_socket.send(b"File downloaded successfully.\n")
    
    # Function to delete file
    def delete_file(self, client_socket, filename):
        """Handles file deletion"""
        filepath = os.path.join("server_storage", filename)
        if not os.path.exists(filepath):
            client_socket.send(b"File not found.\n")
            return
        
        os.remove(filepath)
        client_socket.send(b"File deleted successfully.\n")
    
    # Function to list files
    def list_files(self, client_socket):
        """Lists files in the server's directory."""
        files = os.listdir("server_storage")
        file_list = "\n".join(files)
        client_socket.send(file_list.encode() + b"\n")

# Driver code
if __name__ == "__main__":
    file_server = FileServer(host='127.0.0.1', port=5000)
    file_server.start_server()
