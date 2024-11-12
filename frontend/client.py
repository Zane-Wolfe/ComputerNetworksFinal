## Create the client side of the application

# import libraries
import socket
import os
import hashlib

# create client as class
class FileClient:
    # Constructor
    def __init__(self, server_ip, port):
        self.server_ip = server_ip
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect to server
    def connect(self):
        """Connects to server and authenticates the user"""
        try:
            self.client_socket.connect((self.server_ip, self.port))
            print(f"Connected to server at {self.server_ip}:{self.port}")
            self.authenticate()
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.client_socket.close()
    
    # Authenticate user
    def authenticate(self):
        """Authenticate client by sending username and password."""
        username = input("Enter username: ")
        password = input("Enter password: ")
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Send username and password to server
        self.client_socket.sendall(f"{username}\n".encode())
        self.client_socket.sendall(f"{password_hash}\n".encode())

        # Receive authentication response
        response = self.client_socket.recv(1024).decode()
        print(response)
        if "successful" not in response:
            print("Authentication failed.")
            self.client_socket.close()
        else:
            self.command_loop()
    
    # Send commands
    def command_loop(self):
        """Loop for sending commands to the server."""
        while True:
            command = input("Enter command (UPLOAD, DOWNLOAD, DELETE, DIR, QUIT): ").strip()
            if command == "QUIT":
                self.client_socket.send(b"QUIT")
                print("Disconnected from server.")
                break
            elif command.startswith("UPLOAD"):
                _, filename = command.split()
                self.upload_file(filename)
            elif command.startswith("DOWNLOAD"):
                _, filename = command.split()
                self.download_file(filename)
            elif command.startswith("DELETE"):
                _, filename = command.split()
                self.delete_file(filename)
            elif command == "DIR":
                self.list_files()
            else:
                print("Invalid command.")
    
    # Uploads file
    def upload_file(self, filename):
        """Uploads a file to the server."""
        if not os.path.exists(filename):
            print("File does not exist.")
            return
        
        self.client_socket.sendall(f"UPLOAD {filename}\n".encode())
        response = self.client_socket.recv(1024).decode()
        if "Overwrite?" in response:
            overwrite = input("File exists on server. Overwrite? (y/n): ")
            self.client_socket.sendall(overwrite.encode())
            response = self.client_socket.recv(1024).decode()
        
        if "Ready" in response:
            with open(filename, 'rb') as f:
                while chunk := f.read(1024):
                    self.client_socket.sendall(chunk)
            self.client_socket.sendall(b"EOF")  # Signals end-of-file transfer
            print(self.client_socket.recv(1024).decode())
    
    # Downloads file
    def download_file(self, filename):
        """Downloads a file from the server."""
        self.client_socket.sendall(f"DOWNLOAD {filename}\n".encode())
        response = self.client_socket.recv(1024).decode()

        if "Ready" in response:
            with open(filename, 'wb') as f:
                while True:
                    data = self.client_socket.recv(1024)
                    if data == b"EOF":
                        break
                    f.write(data)
            print("File downloaded successfully.")
        else:
            print(response)  # Error message from server
    
    # Deletes file
    def delete_file(self, filename):
        """Sends a delete command to the server for a specific file."""
        self.client_socket.sendall(f"DELETE {filename}\n".encode())
        response = self.client_socket.recv(1024).decode()
        print(response)  # Server's response (success/failure message)
    
    # Lists files
    def list_files(self):
        """Requests a list of files in the server's directory."""
        self.client_socket.sendall(b"DIR\n")
        response = self.client_socket.recv(4096).decode()
        print("Files on server:\n" + response)
    
    # Disconnect
    def disconnect(self):
        """Gracefully disconnects from the server."""
        self.client_socket.close()

if __name__ == "__main__":
    server_ip = input("Enter the server IP: ")
    port = int(input("Enter the server port: "))
    client = FileClient(server_ip, port)
    client.connect()
