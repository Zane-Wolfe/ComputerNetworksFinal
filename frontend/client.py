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
            try:
                command = input("Enter command (UPLOAD {file}, DOWNLOAD {file}, DELETE {file}, SUBFOLDER {create|delete} {path}, DIR, CD {..|path}, QUIT):\n").strip()
                command_select = command.split()[0].upper()
                if command_select == "QUIT":
                    self.client_socket.send(b"QUIT")
                    print("Disconnected from server.")
                    break
                elif command_select.startswith("UPLOAD"):
                    _, filename = command.split()
                    self.upload_file(filename)
                elif command_select.startswith("DOWNLOAD"):
                    _, filename = command.split()
                    self.download_file(filename)
                elif command_select.startswith("DELETE"):
                    _, filename = command.split()
                    self.delete_file(filename)
                elif command_select.startswith("SUBFOLDER"):
                    _, cmd, path = command.split()
                    self.manage_subfolders(cmd, path)
                elif command_select == "DIR":
                    self.list_files()
                elif command_select.startswith("CD"):
                    _, path = command.split()
                    self.change_directory(path)
                else:
                    print("Invalid command.")
            except Exception as e:
                print("Invalid command! Please provide valid arguments!")

    # Uploads file
    def upload_file(self, filename):
        """Uploads a file to the server."""
        if not os.path.exists(filename):
            print("File does not exist.")
            return

        self.client_socket.sendall(f"UPLOAD {filename}\n".encode())
        response = self.client_socket.recv(1024).decode()
        print(response)
        if "Overwrite?" in response:
            overwrite = input("File exists on server. Overwrite? (y/n): ")
            self.client_socket.sendall(overwrite.encode())
            response = self.client_socket.recv(1024).decode()

        if "Ready" in response:
            with open(filename, 'rb') as f:
                while chunk := f.read(1024):
                    self.client_socket.sendall(chunk)
            self.client_socket.sendall(b"EOF")  # Send "EOF" after the file is done
            print(self.client_socket.recv(1024).decode())

    # Downloads file
    def download_file(self, filename):
        """Downloads a file from the server."""
        if os.path.exists(filename):
           response = input("File exists on your computer! Do you wish to overwrite? (y/n): ")
           if response == "y":
               print("Overwriting "+filename)
           else:
               print("Canceling download\n")
               return

        self.client_socket.sendall(f"DOWNLOAD {filename}\n".encode())
        response = self.client_socket.recv(1024).decode()
        if "Ready" in response:
            print("Ready to receive file")
            with open(filename, 'wb') as f:
                buffer = b""
                while True:
                    data = self.client_socket.recv(1024)
                    if b"EOF" in data:
                        buffer += data.split(b"EOF")[0]  # Write everything before "EOF"
                        f.write(buffer)
                        break
                    buffer += data
                    f.write(buffer)
                    buffer = b""  # Reset buffer after writing to the file
            print("File downloaded\n")
        else:
            print("File not found!\n")

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
        if response == "":
            print("There are no files on the server! Upload files to view them here")
            return
        files = []
        directories = []
        for path in response.split('\n'):
            if path == '':
                continue
            if '.' in path.split('/')[-1]:  # Checks for a file extension in the last part of the path
                files.append(path)
            else:
                directories.append(path)

        files.sort()
        directories.sort()
        print("Files:")
        for file in files:
            print(file)
        print("\nSub-Directories:")
        for directory in directories:
            print(directory)
        print()

    # Disconnect
    def disconnect(self):
        """Gracefully disconnects from the server."""
        self.client_socket.close()

    def manage_subfolders(self, cmd, path):
        cmd = cmd.upper()
        path = path.lower()
        self.client_socket.sendall(f"SUBFOLDER {cmd} {path}\n".encode())
        response = self.client_socket.recv(1024).decode()

        if cmd == "CREATE":
            if "exists" in response:
                print("Subfolder already exists!")
            elif "successfully" in response:
                print("Subfolder created successfully!")
        elif cmd == "DELETE":
            if "not found" in response:
                print("Subfolder does not exist!")
            elif "successfully" in response:
                print("Subfolder deleted successfully!")

    def change_directory(self, path):
        self.client_socket.sendall(f"CD {path}\n".encode())
        response = self.client_socket.recv(1024).decode()
        print(response)


if __name__ == "__main__":
    # server_ip = input("Enter the server IP: ")
    # port = int(input("Enter the server port: "))
    server_ip = '127.0.0.1'
    port = 4455
    client = FileClient(server_ip, port)
    client.connect()
