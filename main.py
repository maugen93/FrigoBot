import os

from dotenv import load_dotenv

import bot


if __name__ == '__main__':
    load_dotenv()
    token = os.environ['TELEGRAM_BOT_TOKEN']
    db_path = os.environ['DB_PATH']

    bot.start_bot(token, db_path)















