import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder,CommandHandler,MessageHandler,ContextTypes,filters
from fbs_bot.engine import Engine
engine=Engine()
async def start(update:Update, context:ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Ola! Sou o assistente da FBS Distribuicao.")
async def text(update:Update, context:ContextTypes.DEFAULT_TYPE): await update.message.reply_text(engine.handle_message(update.effective_chat.id,update.message.text))
def main():
    from dotenv import load_dotenv
    load_dotenv()
    token=os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN nao definido. Crie o arquivo .env a partir do .env.example.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print("Bot iniciado. Aguardando mensagens (Ctrl+C para parar)...", flush=True)
    app=ApplicationBuilder().token(token).build(); app.add_handler(CommandHandler("start",start)); app.add_handler(CommandHandler("ajuda",start)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text)); app.run_polling()
if __name__=="__main__": main()
