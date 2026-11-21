import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from fbs_bot.engine import Engine

LOGGER = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("Olá! Sou o assistente da FBS Distribuição.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message:
        await message.reply_text(
            "Posso consultar embarques, agendamentos, notas fiscais, pátio, "
            "ocorrências, estadia e transportadoras. Envie o identificador "
            "do registro junto com sua pergunta."
        )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if not message or not message.text or not chat:
        return
    engine = context.application.bot_data["engine"]
    await message.reply_text(engine.handle_message(chat.id, message.text))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.error:
        error = context.error
        LOGGER.error(
            "Unhandled Telegram update error",
            exc_info=(type(error), error, error.__traceback__),
        )
    else:
        LOGGER.error("Telegram update failed without an exception object")


def build_application(token: str, engine: Engine) -> Application:
    application = ApplicationBuilder().token(token).build()
    application.bot_data["engine"] = engine
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ajuda", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)
    )
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN não definido. "
            "Crie o arquivo .env a partir do .env.example."
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    engine = Engine()
    application = build_application(token, engine)
    print("Bot iniciado. Aguardando mensagens (Ctrl+C para parar)...", flush=True)
    application.run_polling()


if __name__ == "__main__":
    main()
