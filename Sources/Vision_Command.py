import socket
import time

def send_command(IP: str, PORT: int, command: str, wait=0.1):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            s.connect((IP, PORT))
            s.sendall(command.encode("utf-8"))
            time.sleep(wait)
            return s.recv(1024).decode().strip()
    except Exception as e:
        return f"TCP Error: {e}"   
    
# serial = "600403008A2504C2027267"
# HOST_IP = "169.254.148.226"
# PORT = 8500
# response = send_command(HOST_IP, PORT, 'T2\r')

# print(response)