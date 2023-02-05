from modification_tracker import settings

import uuid

import requests
from telegram import Update
from telegram.ext import filters
from telegram.ext import ContextTypes, Application, MessageHandler, CommandHandler

secret_keys = dict()
authorized_users = set()
targets = dict()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, введите секретный ключ для продолжения работы")
	secret_keys[update.effective_chat.id] = str(uuid.uuid4())
	print(f"Секретный ключ для {update.effective_chat.username}: {secret_keys[update.effective_chat.id]}")


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat_id, text = update.effective_chat.id, update.message.text
	if chat_id not in secret_keys or chat_id in authorized_users:
		return
	if text != secret_keys[chat_id]:
		await context.bot.send_message(chat_id=chat_id, text="Неправильный ключ авторизации")
	else:
		authorized_users.add(chat_id)
		targets[chat_id] = []
		await context.bot.send_message(chat_id=chat_id, text="Успех")


async def add_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat_id, text = update.effective_chat.id, update.message.text
	if chat_id not in authorized_users:
		return

	if len(context.args) != 1:
		await context.bot.send_message(chat_id=chat_id, text="Неправильное число аргументов")
		return

	r = requests.get(context.args[0])
	targets[chat_id].append({
		"url": context.args[0],
		"last_modified": r.headers["last-modified"]
	})
	await context.bot.send_message(chat_id=chat_id, text="Успех")


async def check_modification(context: ContextTypes.DEFAULT_TYPE):
	for chat_id, pages in targets.items():
		for page in pages:
			r = requests.get(page["url"])
			if page["last_modified"] != r.headers["last-modified"]:
				await context.bot.send_message(chat_id=chat_id, text=f"Страница {page['url']} была обновлена")
				page["last_modified"] = r.headers["last-modified"]


if __name__ == "__main__":
	application = Application.builder().token(settings.ACCESS_TOKEN).build()
	job_queue = application.job_queue
	
	start_handler = CommandHandler("start", start)
	add_target_handler = CommandHandler("add", add_target)
	text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), text)

	application.add_handler(start_handler)
	application.add_handler(text_handler)
	application.add_handler(add_target_handler)

	check_modification_job = job_queue.run_repeating(check_modification, interval=5)

	application.run_polling()
