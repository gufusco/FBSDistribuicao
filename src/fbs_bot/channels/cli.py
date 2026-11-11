import argparse
import sys
from fbs_bot.engine import Engine
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p=argparse.ArgumentParser(); p.add_argument("--chat-id",type=int,default=1); a=p.parse_args()
e=Engine(); print("Assistente FBS (Ctrl+C para sair)")
while True:
    try: print("Bot:",e.handle_message(a.chat_id,input("Voce: ")))
    except (EOFError,KeyboardInterrupt): break
