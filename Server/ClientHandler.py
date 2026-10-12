from UserManager import UserManager
import time

class ClientHandler:
    def __init__(self, client_socket, address):
        self.socket = client_socket
        self.address = address
        self.username = None
        self.user_manager = UserManager()

    def broadcast_user_list(self):   #saljemo listu svim povezanim korisnicima ko je online
        users_string = self.user_manager.get_all_users_string()
        message = f"USERS {users_string}"

        for data in self.user_manager.active_users.values():
            try:
                data["socket"].send((message + "\n").encode("ascii"))
            except:
                pass

    def send(self, message):
        try:
            self.socket.send((message + "\n").encode("ascii"))
        except:
            pass

    def handle_registracija(self, parts):
        if len(parts) != 2:
            return

        username = parts[1]
        success, voice_port = self.user_manager.register_user(username, self.socket, self.address[0])

        if not success:
            self.send("ERROR Username taken")
            self.socket.close()
            return

        self.username = username
        self.send(f"REGISTERED {voice_port}")

        time.sleep(0.1)

        all_users = self.user_manager.get_all_users_string()
        self.send(f"USERS {all_users}") # salje listu direktno novom klijentu

        self.broadcast_user_list() # salje osvezenu listu ostalima
        print(f"{username} connected.")

    def handle_poziv(self, parts):
        primalac_name = parts[1]
        target = self.user_manager.get_user_data(primalac_name)
        caller = self.user_manager.get_user_data(self.username)
        if target and target["status"] == "online":
            self.user_manager.set_status(self.username, "busy")
            self.user_manager.set_status(primalac_name, "busy")   #pozvanom korisniku se salje poruka od kog je primio poziv
            target["socket"].send(f"CALL {self.username} {caller['ip']} {caller['voice_port']}\n".encode("ascii"))
            self.broadcast_user_list()


    def handle_prihvati_poziv(self, parts):
        caller_username = parts[1]
        accepter = self.user_manager.get_user_data(self.username)
        caller = self.user_manager.get_user_data(caller_username)
        self.user_manager.active_calls[self.username] = caller_username
        self.user_manager.active_calls[caller_username] = self.username

        if caller:  #saljemo korisniku koji je zapoceo poziv ime, ip ad i port
            caller["socket"].send(f"ACCEPTED {self.username} {accepter['ip']} {accepter['voice_port']}\n".encode("ascii"))
            print(f"{self.username} accepted call from {caller_username}")


    def handle_reject(self, parts):
        caller_username = parts[1]
        self.user_manager.set_status(self.username, "online")
        self.user_manager.set_status(caller_username, "online")

        caller = self.user_manager.get_user_data(caller_username)
        if caller:
            caller["socket"].send(f"REJECTED {self.username}\n".encode("ascii"))

        self.broadcast_user_list()  #azuriranje tabele korisnika
        print(f"{self.username} rejected call from {caller_username}")

    def handle_end_call(self):
        caller = self.username  #osoba koja je prekinula
        peer = self.user_manager.active_calls.pop(caller, None)  #njen sagovornik

        self.user_manager.set_status(caller, "online")

        if peer:
            self.user_manager.active_calls.pop(peer, None)   #brise i drugu stranu iz liste poziva
            self.user_manager.set_status(peer, "online")
            #Server salje poruku ENDED onoj drugoj osobi.
            peer_data = self.user_manager.get_user_data(peer)
            if peer_data:
                try:
                    peer_data["socket"].send(f"ENDED {caller}\n".encode("ascii"))
                except:
                    pass

        self.broadcast_user_list()
        print(f"Call ended between {caller} and {peer}. Connection stays alive.")


    def run(self):
        try:
            while True:
                data = self.socket.recv(1024)
                if not data: break

                raw = data.decode("ascii").strip()
                parts = raw.split()
                if not parts: continue

                command = parts[0].upper()  #recnik
                command_map = {
                    "REGISTER": self.handle_registracija,
                    "CALL": self.handle_poziv,
                    "ACCEPT": self.handle_prihvati_poziv,
                    "REJECT": self.handle_reject,
                    "LIST": lambda p: self.broadcast_user_list(),
                    "END_CALL": lambda p: self.handle_end_call()
                }

                if command in command_map:
                    command_map[command](parts)
                else:
                    self.send("ERROR Komanda ne postoji!")
        except Exception as e:
            print("SERVER ERROR:", e)
        finally:
            self.cleanup()

    def cleanup(self):  #poziva se prilikom prekida veze ili u slucaju greske
        if self.username:
            print(f"Cleaning up for user: {self.username}")
            peer = self.user_manager.active_calls.pop(self.username, None)
            #Ako je korisnik bio u razgovoru dok je izasao, pronalazimo sagovornika (peer) i saljemo mu poruku ended
            if peer:
                self.user_manager.active_calls.pop(peer, None)
                self.user_manager.set_status(peer, "online")
                peer_data = self.user_manager.get_user_data(peer)
                if peer_data:
                    try:
                        peer_data["socket"].send(f"ENDED {self.username}\n".encode("ascii"))
                    except Exception as e:
                        print(f"Could not send ENDED to peer {peer}: {e}")
            try:
                self.user_manager.remove_user(self.username)
            except Exception as e:
                print(f"Error removing user from manager: {e}")
        try:
            self.broadcast_user_list()
        except:
            pass
        try:
            self.socket.close()
        except:
            pass
        print(f"Cleanup finished for {self.username if self.username else 'Unknown'}")
