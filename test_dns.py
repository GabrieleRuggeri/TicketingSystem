import socket

host = "db.apvodkpbtkkfveyyrzgj.supabase.co"

try:
    print("Resolving:", host)
    ip = socket.gethostbyname(host)
    print("Resolved IP:", ip)
except Exception as e:
    print("DNS resolution failed:", e)