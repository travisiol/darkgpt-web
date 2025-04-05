import telebot

TOKEN = '7795830648:AAFIUU0SG25DqYP23JCnLZGIbbddNCWMJnw'  # Ton token
bot = telebot.TeleBot(TOKEN)

@bot.channel_post_handler(func=lambda message: True)
def handle_channel_post(message):
    print(f"L'ID de ton canal est : {message.chat.id}")

bot.polling()
