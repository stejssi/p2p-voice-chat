import threading
import numpy as np
import sounddevice as sd
import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import socket
import json

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {"HOST": "127.0.0.1", "PORT": 9000, "CHANNELS": 1, "DTYPE": "float32", "BLOCKSIZE": 2048}

HOST = config['HOST']
PORT = config['PORT']
CHANNELS = config['CHANNELS']
DTYPE = config['DTYPE']
BLOCKSIZE = config['BLOCKSIZE']

class VoiceChatGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Voice Chat")
        self.geometry("500x600")
        ctk.set_appearance_mode("dark")

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.voice_running = False
        self.voice_port = None
        self.is_muted = False
        self.peer_ip = None
        self.peer_port = None
        self.peer_username = None

        self.setup_ui()

    def setup_ui(self):
        self.label_title = ctk.CTkLabel(self, text="Welcome!", font=("Arial", 24, "bold"))
        self.label_title.pack(pady=20)

        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=10, padx=20, fill="x")

        self.entry_username = ctk.CTkEntry(self.frame_login, placeholder_text="Enter username...")
        self.entry_username.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.btn_connect = ctk.CTkButton(self.frame_login, text="Connect", command=self.connect_to_server)
        self.btn_connect.pack(side="right", padx=10)

        self.label_users = ctk.CTkLabel(self, text="Active users", font=("Arial", 14))
        self.label_users.pack(pady=(10, 0))

        style = ttk.Style()
        style.theme_use("default")
        table_font = ("Arial", 16)
        header_font = ("Arial", 16, "bold")
        style.configure("Treeview",background="#2b2b2b",foreground="white",fieldbackground="#2b2b2b",
                        borderwidth=0,font = table_font,rowheight=30,)
        style.configure("Treeview.Heading",background="#333333",foreground="white",font=header_font)
        style.map("Treeview", background=[('selected', '#1f538d')])

        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.user_table = ttk.Treeview(self.table_frame, columns=("User", "Status"), show="headings", height=8)
        self.user_table.heading("User", text="Username")
        self.user_table.heading("Status", text="Status")
        self.user_table.column("User", anchor="center", width=150)
        self.user_table.column("Status", anchor="center", width=100)

        self.user_table.pack(side="left", fill="both", expand=True)

        self.scrollbar = ctk.CTkScrollbar(self.table_frame, command=self.user_table.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.user_table.configure(yscrollcommand=self.scrollbar.set)

        self.frame_controls = ctk.CTkFrame(self)
        self.frame_controls.pack(pady=20, padx=20, fill="x")

        self.target_select = ctk.CTkComboBox(self.frame_controls, values=["Choose user..."])
        self.target_select.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_call = ctk.CTkButton(self.frame_controls, text="CALL", fg_color="green", command=self.make_call)
        self.btn_call.pack(side="right", padx=5)

        self.btn_mute = ctk.CTkButton(self.frame_controls, text="MUTE", fg_color="orange", command=self.toggle_mute)
        self.btn_end = ctk.CTkButton(self.frame_controls, text="END CALL", fg_color="#8B0000", command=self.end_call)

        self.incoming_frame = ctk.CTkFrame(self, fg_color="#2B2B2B", border_width=2, border_color="green")
        self.incoming_label = ctk.CTkLabel(self.incoming_frame, text="Incoming call...")
        self.incoming_label.pack(pady=5)

        self.btn_accept = ctk.CTkButton(self.incoming_frame, text="Accept", fg_color="green", width=100,
                                        command=self.accept_call_ui)
        self.btn_accept.pack(side="left", padx=20, pady=10)

        self.btn_reject = ctk.CTkButton(self.incoming_frame, text="Reject", fg_color="red", width=100,
                                        command=self.reject_call_ui)
        self.btn_reject.pack(side="right", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self, text="Status: Offline", text_color="gray")
        self.status_label.pack(pady=10)

    def connect_to_server(self):
        username = self.entry_username.get() #izvlacimo tekst koji smo upisali
        self.username = username.strip()

        if not username:
            messagebox.showwarning("Warning", "Please enter a username!")
            return

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  #TCP protokol
        self.client.settimeout(5)
        #TCP konekcija
        try:
            self.client.connect((HOST, PORT))
            self.client.send(f"REGISTER {username}".encode('ascii'))
            self.client.settimeout(None)

            self.status_label.configure(text=f"Connected as: {username}", text_color="cyan")  #menjamo tekst iz offline u connected as...
            self.btn_connect.configure(state="disabled")
            self.entry_username.configure(state="disabled")

            threading.Thread(target=self.receive_messages, daemon=True).start()  #pokrece slusanje poruka u pozadini da ne zakoči prozor

        except ConnectionRefusedError:
            messagebox.showerror("Error", f"Server at {HOST}:{PORT} is not running or refused the connection.")
            self.status_label.configure(text="Status: Server unavailable", text_color="red")
            self.reset_socket_ui()

        except socket.timeout:
            messagebox.showerror("Error", "Connection to the server timed out.")
            self.status_label.configure(text="Status: Timeout", text_color="red")
            self.reset_socket_ui()

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.status_label.configure(text="Status: Error", text_color="red")
            self.reset_socket_ui()

    def reset_socket_ui(self):    #kada pokusavamo da se povezemo, a ne uspemo
        self.client.close()
        self.btn_connect.configure(state="normal")
        self.entry_username.configure(state="normal")

    def handle_server_disconnect(self):  #kada server pukne ili padne pa resetujemo sve
        self.voice_running = False
        try:
            self.client.close()
        except:
            pass
        self.status_label.configure(text="Connection stopped. Server was shut down.", text_color="red")
        self.incoming_frame.pack_forget()
        self.reset_ui_after_call()
        self.btn_connect.configure(state="normal")
        self.entry_username.configure(state="normal")
        self.is_muted = False
        self.btn_mute.configure(text="MUTE", fg_color="orange")
        self.peer_ip = None
        self.peer_port = None
        self.peer_username = None

    def receive_messages(self):
        while True:
            try:
                data = self.client.recv(4096)  #cekamo podatke sa mreze
                if not data:
                    self.after(0, self.handle_server_disconnect)
                    break

                messages = data.decode('ascii').strip().split('\n')
                for msg in messages:
                    parts = msg.split()
                    if not parts:
                        continue
                    command = parts[0]

                    if command == "REGISTERED":
                        self.voice_port = int(parts[1])
                    elif command == "USERS":
                        self.update_user_list(parts[1:])  #lista svih koji su online
                    elif command == "CALL":
                        self.peer_username, self.peer_ip, self.peer_port = parts[1], parts[2], int(parts[3])
                        self.after(0, self.incoming_call_ui)
                    elif command == "ACCEPTED":
                        self.peer_username, self.peer_ip, self.peer_port = parts[1], parts[2], int(parts[3])
                        self.after(0, lambda: self.start_voice_chat(is_sender=True))
                    elif command == "REJECTED":
                        self.after(0, lambda: self.status_label.configure(
                            text=f"{parts[1]} rejected the call", text_color="red"
                        ))
                        self.after(0, self.reset_ui_after_call)
                    elif command == "ENDED":
                        prekinuo = parts[1] if len(parts) > 1 else ""
                        self.after(0, lambda: self.status_label.configure(
                            text=f"{prekinuo} ended the call.", text_color="orange"
                        ))
                        self.after(0, self.stop_audio_locally)

            except Exception as e:
                print(f"Greška u prijemu: {e}")
                self.after(0, self.handle_server_disconnect)
                break

    def update_user_list(self, users):
        #prvo brisemo sve redove u tabeli
        for item in self.user_table.get_children():
            self.user_table.delete(item)

        moje_ime = self.username
        imena_za_poziv = []

        for u in users:
            if ":" in u:
                name, status = u.split(":")
                self.user_table.insert("", "end", values=(name, status))
                if name.strip().lower() != moje_ime.lower():
                    imena_za_poziv.append(name)
        #azuriramo cmbbox
        if imena_za_poziv:
            self.target_select.configure(values=imena_za_poziv)
            if self.target_select.get() in ["Choose user...", "", "No users online"]:
                self.target_select.set(imena_za_poziv[0])
        else:
            self.target_select.configure(values=["No users online"])
            self.target_select.set("No users online")

    def make_call(self):
        target = self.target_select.get()  #uzimamo ime korisnika koje je odabrano u cmbboxu
        if target and target != "Choose user..." and target != self.username:
            self.client.send(f"CALL {target}".encode('ascii'))

    def incoming_call_ui(self):   #vizuelno nam prikazuje poziv
        self.incoming_label.configure(text=f"Call from: {self.peer_username}")
        self.incoming_frame.pack(pady=10, before=self.status_label)
        self.btn_call.configure(state="disabled")

    def accept_call_ui(self):
        self.incoming_frame.pack_forget()    #sakrivamo panel za dolazni poziv
        self.client.send(f"ACCEPT {self.peer_username}".encode('ascii'))
        self.start_voice_chat(is_sender=False)    #false jer ne zapocinjemo mi poziv nego prihvatamo
        self.show_call_controls()

    def reject_call_ui(self):
        self.incoming_frame.pack_forget()
        self.client.send(f"REJECT {self.peer_username}".encode('ascii'))
        self.btn_call.configure(state="normal")

    def show_call_controls(self):   #sakrivamo listu korisnika i dodajemo mute i end
        self.target_select.pack_forget()
        self.btn_call.pack_forget()
        self.btn_mute.pack(side="left", padx=10, expand=True)
        self.btn_end.pack(side="right", padx=10, expand=True)

    def reset_ui_after_call(self):
        self.btn_mute.pack_forget()
        self.btn_end.pack_forget()
        self.target_select.pack(side="left", padx=5, expand=True, fill="x")
        self.btn_call.pack(side="right", padx=5)
        self.btn_call.configure(state="normal")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.configure(text="UNMUTE", fg_color="red")
            self.status_label.configure(text="MUTE", text_color="orange")
        else:
            self.btn_mute.configure(text="MUTE", fg_color="orange")
            if self.voice_running:
                self.status_label.configure(text="IN CALL", text_color="red")


    def end_call(self):
        if self.voice_running:
            self.client.send("END_CALL".encode('ascii'))
            self.stop_audio_locally()

    def stop_audio_locally(self):
        self.voice_running = False
        self.is_muted = False
        self.after(0, self.reset_ui_after_call)
        self.after(0, lambda: self.status_label.configure(text="Ready", text_color="cyan"))

    # UDP protokol
    def start_voice_chat(self, is_sender):
        if self.voice_running: return
        self.voice_running = True
        self.status_label.configure(text="IN CALL", text_color="red")
        self.show_call_controls()

        threading.Thread(target=self.send_voice, daemon=True).start()   #jedan salje moj glas
        threading.Thread(target=self.receive_voice, daemon=True).start()  #drugi prima glas sagovornika

    def send_voice(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        def callback(indata, frames, time, status):
            if status:
                print(status)
            if self.voice_running and self.peer_ip and self.peer_port:
                try:
                    if self.is_muted:   #ako smo mjutovani saljemo nule(tisinu)
                        data_to_send = np.zeros_like(indata)
                        udp.sendto(data_to_send.tobytes(), (self.peer_ip, self.peer_port))
                    else:
                        udp.sendto(indata.tobytes(), (self.peer_ip, self.peer_port))
                except Exception as e:
                    print("ERROR while trying to send voice:", e)
        try:  #otvaramo mikrofon sa ovim podesavanjima
            with sd.InputStream(samplerate=48000,channels=CHANNELS,dtype=DTYPE,blocksize=BLOCKSIZE,callback=callback):
                while self.voice_running:
                    sd.sleep(100)
        except Exception as e:
            print("ERROR in InputStream:", e)
        finally:
            udp.close()

    def receive_voice(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind(('', self.voice_port))
        udp.settimeout(1.0)

        stream = sd.OutputStream(samplerate=48000, channels=CHANNELS, dtype=DTYPE, blocksize=BLOCKSIZE)

        with stream:
            while self.voice_running:
                try:
                    data, _ = udp.recvfrom(8192)   #cekamo paket sa mreze
                    audio_data = np.frombuffer(data, dtype=np.float32).reshape(-1, CHANNELS)   #bajtove iz mreze pretvaramo u brojeve
                    stream.write(audio_data * 2)    #pusta zvuk na zvucnike
                except socket.timeout:
                    continue
                except:
                    break

        udp.close()