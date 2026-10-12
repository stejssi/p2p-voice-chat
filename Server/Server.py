import socket
import threading
from ClientHandler import ClientHandler

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #IPv4 i TCP

    def start(self):
        self.server_socket.bind((self.host, self.port))    #soket se vezuje za ip i port
        self.server_socket.listen()
        print("Server is waiting...")

        while True:
            client_socket, address = self.server_socket.accept()
            print("Client connected.")

            handler = ClientHandler(client_socket, address)
            thread = threading.Thread(target=handler.run)      #za svakog klijenta novanit
            thread.start()


if __name__ == "__main__":
    server = Server("172.20.10.9", 9000)
    server.start()