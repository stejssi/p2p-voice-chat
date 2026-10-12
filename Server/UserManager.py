import threading

class UserManager:
    #Singleton
    _instance = None
    _lock = threading.Lock()   #samo 1 nit kreira intancu

    def __new__(cls):   #kreiranje instance klase
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UserManager, cls).__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):   #za pocetno stanje klase
        self.active_users = {}
        self.used_ports = set()
        self.active_calls = {}

    def register_user(self, username, client_socket, ip):
        with self._lock:   #zakljucavamo da bi radila samo 1 nit
            if username in self.active_users:
                return False, None
            voice_port = 5000
            while voice_port in self.used_ports:
                voice_port += 1

            self.used_ports.add(voice_port)
            self.active_users[username] = {
                "socket": client_socket,
                "ip": ip,
                "voice_port": voice_port,
                "status": "online"
            }
            return True, voice_port

    def remove_user(self, username):   #brisemo broj porta iz liste zauzetih portova
        with self._lock:
            if username in self.active_users:
                port = self.active_users[username]["voice_port"]
                if port in self.used_ports:
                    self.used_ports.remove(port)
                del self.active_users[username]
                return True
            return False

    def get_user_data(self, username):
        with self._lock:
            return self.active_users.get(username)

    def set_status(self, username, status):
        with self._lock:
            if username in self.active_users:
                self.active_users[username]["status"] = status

    def get_all_users_string(self):
        with self._lock:
            return " ".join([f"{u}:{d['status']}" for u, d in self.active_users.items()])