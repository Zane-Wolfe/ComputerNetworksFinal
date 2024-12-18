## Create the server side of the application
import signal
# import libraries
import socket
import threading
import os
import hashlib
import shutil
import time
import sys
from statistics_logger import StatisticsLogger




def format_size(size_in_bytes):
    """Convert file size in bytes to a human-readable format."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = size_in_bytes
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


class FileServer:
    # Constructor
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # to track active clients
        self.current_client_dir = {}
        self.running = True
        self.logger = StatisticsLogger()

    # Function to start server
    def start_server(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown_server)

        while self.running:
            try:
                # Shutdown the server
                self.server_socket.settimeout(1)  # Avoid indefinite blocking
                client_socket, client_address = self.server_socket.accept()
                print(f"New connection from {client_address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                self.clients[client_socket] = client_thread
                self.current_client_dir[client_socket] = "server_storage"
                client_thread.start()
            except socket.timeout:
                continue
        self.shutdown_server()

    # Graceful shutdown method
    def shutdown_server(self, signum=None, frame=None):
        print("Shutting down server...")
        self.running = False  # Stop accepting new connections
        for client_socket in list(self.clients.keys()):  # Close active connections
            try:
                client_socket.close()
            except Exception as e:
                print(f"Error closing client connection: {e}")

        self.server_socket.close()
        self.logger.save_to_file("server_statistics.csv")  # Save logs
        print("Server stopped gracefully. Logs saved.")
        sys.exit(0)

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
                if command.lower() == "quit":
                    # Client quit
                    break
                if command.lower() == "shutdown":
                    self.running = False
                    client_socket.send(b"Server Shutdown\n")
                    break

                self.process_command(client_socket, command, args)
            except Exception as e:
                print(f"Error: {e}")
                client_socket.send(b"An error occurred.")
                break

        self.clients.pop(client_socket)
        self.current_client_dir.pop(client_socket)
        client_socket.close()


    def authenticate(self, client_socket):
        """Basic authentication: Ask for username and password."""
        username = client_socket.recv(1024).decode().strip()
        password_hash = client_socket.recv(1024).decode().strip()

        # Check credentials
        if username == "user" and password_hash == hashlib.sha256(b"pass").hexdigest():
            client_socket.send(b"Authentication successful.\n")
            return True
        else:
            client_socket.send(b"Authentication failed.\n")
            client_socket.close()
            return False

    # Function to process commands
    def process_command(self, client_socket, command, args):
        command = command.upper()
        if command == "UPLOAD":
            self.upload_file(client_socket, args[0])
        elif command == "DOWNLOAD":
            self.download_file(client_socket, args[0])
        elif command == "DELETE":
            self.delete_file(client_socket, args[0])
        elif command == "DIR":
            self.list_files(client_socket)
        elif command == "SUBFOLDER":
            self.sub_folder(client_socket, args[0], args[1])
        elif command == "CD":
            self.change_directory(client_socket, args[0])
        else:
            client_socket.send(b"Invalid command.\n")

    # Function to upload file
    def upload_file(self, client_socket, filename):
        """Handles file upload from client."""
        filepath = self.current_client_dir[client_socket]
        filepath = os.path.join(filepath, filename)
        if os.path.exists(filepath):
            client_socket.send(b"File exists. Overwrite? (y/n): ")
            response = client_socket.recv(1024).decode().strip().lower()
            if response != 'y':
                client_socket.send(b"Upload cancelled.\n")
                return
        print("Ready to receive file")
        client_socket.send(b"Ready to receive file.\n")
        response_time = 0
        file_size = 0
        start_time = self.logger.start_timer()
        with open(filepath, 'wb') as f:
            buffer = b""
            while True:
                data = client_socket.recv(1024)
                if response_time == 0:
                    response_time = time.time() - start_time
                if b"EOF" in data:
                    buffer += data.split(b"EOF")[0]  # Write everything before "EOF"
                    f.write(buffer)
                    break
                buffer += data
                f.write(buffer)
                file_size += len(data)
                buffer = b""  # Reset buffer after writing to the file
        print("File uploaded")

        # End timer and calculate response time
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Format file_size
        formatted_size = format_size(file_size)

        # Format the response string
        response_message = f"File uploaded of size {formatted_size} successfully in {elapsed_time:.3f} seconds!\n"
        client_socket.send(response_message.encode())

        # Log the upload operation
        self.logger.end_timer(
            start_time=start_time,
            operation="UPLOAD",
            filename=filename,
            file_size=file_size,
            elapsed_time=elapsed_time,
            response_time=response_time
        )

    # Function to download file
    def download_file(self, client_socket, filename):
        """Handles file download to client."""
        filepath = self.current_client_dir[client_socket]
        filepath = os.path.join(filepath, filename)
        if not os.path.exists(filepath):
            client_socket.send(b"File not found.\n")
            return

        file_size = os.path.getsize(filepath)
        start_time = self.logger.start_timer()

        client_socket.send(b"Ready to send file.")
        with open(filepath, 'rb') as f:
            while chunk := f.read(1024):
                client_socket.send(chunk)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Log the operation
        self.logger.end_timer(
            start_time=start_time,
            operation="DOWNLOAD",
            filename=filename,
            file_size=file_size,
            elapsed_time=elapsed_time,
            response_time=elapsed_time
        )

        client_socket.send(b"EOF")
        # Format the response string
        # Format file_size
        time.sleep(0.5)
        formatted_size = format_size(file_size)
        response_message = f"File uploaded of size {formatted_size} successfully in {elapsed_time:.3f} seconds!\n"
        client_socket.send(response_message.encode())

    # Function to delete file
    def delete_file(self, client_socket, filename):
        """Handles file deletion"""
        filepath = self.current_client_dir[client_socket]
        filepath = os.path.join(filepath, filename)
        if not os.path.exists(filepath):
            client_socket.send(b"File not found.\n")
            return

        os.remove(filepath)
        client_socket.send(b"File deleted successfully.\n")


    # Function to list files
    def list_files(self, client_socket):
        """Lists files in the server's directory."""
        filepath = self.current_client_dir[client_socket]
        files = os.listdir(filepath)
        file_list = "\n".join(files)
        client_socket.send(file_list.encode() + b"\n")

    def sub_folder(self, client_socket, command, path):
        """Create or delete a sub folder."""
        path = "server_storage/" + path.lower()
        if command == 'CREATE':
            if os.path.exists(path):
                client_socket.send(b"Folder already exists!\n")
                return
            os.mkdir(path)
            client_socket.send(b"Folder created successfully.\n")
        elif command == 'DELETE':
            if not os.path.exists(path):
                client_socket.send(b"Folder not found.\n")
                return
            shutil.rmtree(path)
            client_socket.send(b"Folder deleted successfully.\n")

    def change_directory(self, client_socket, directory):
        filepath = self.current_client_dir[client_socket]
        directory = directory.lower()
        if directory == "..":
            if filepath == "server_storage":
                client_socket.send(b"You are already at the root directory!\n")
            else:
                newPath = os.path.dirname(filepath)
                self.current_client_dir[client_socket] = newPath
                client_socket.send(b"File path changed to: "+newPath.encode()+b"\n")
        else:
            filepath = os.path.join(filepath, directory)
            if os.path.exists(filepath):
                client_socket.send(b"File path changed to: "+filepath.encode()+b"\n")
                self.current_client_dir[client_socket] = filepath
            else:
                client_socket.send(b"File path not found.\n")

# Driver code
if __name__ == "__main__":
    server_ip = '127.0.0.1'
    # server_ip = '192.168.123.202'
    file_server = FileServer(host=server_ip, port=4456)
    file_server.start_server()
