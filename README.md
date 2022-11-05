# BenalUMA Bot

**BenalUMA Bot** is a Telegram bot written in Python and built on the [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) API (v13.11). It is deployed in Render (previously in Heroku) and is supported by a Google Firebase Database. 

The purpose of this bot is to maintain car sharing tasks within a community of people (mostly students) from Benalmádena (Spain) that usually go to the University of Málaga. The bot itself can be found at [@BenalUMA_bot](https://t.me/BenalUMA_bot).
## Run Locally

First, clone the project

```bash
git clone https://github.com/Pablo097/BenalUMA-bot.git BenalUMAbot
```

Go inside the project folder and install the dependencies through the `requirements.txt` file
```bash
pip install -r requirements.txt
```

In the parent folder to the one where you have cloned the project (`BenalUMAbot`), create a file named `.env` where the environment variables will be stored. The Telegram bot token is obtained talking to the [@BotFather](https://t.me/BotFather), and the Firebase authentication information is downloaded from the Firebase project configuration. The user with the `ADMIN_CHAT_ID` will be able to use administrator-level commands, and if `DEBUG_GROUP_CHAT_ID` is configured, some debug messages will be sent to that group. The content of the `.env` file must look like this:
```
TOKEN="<your_telegram_bot_token>"
ADMIN_CHAT_ID="<your_telegram_chat_id>"
DEBUG_GROUP_CHAT_ID="your_debug_group_telegram_chat_id"
FIREBASE_PROJECT_ID="<...>"
FIREBASE_PRIVATE_KEY_ID="<...>"
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<...>\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL="<...>"
FIREBASE_CLIENT_ID="<...>"
FIREBASE_TOKEN_URI="https://oauth2.googleapis.com/token"
FIREBASE_DATABASE_URL="<....firebasedatabase.app/>"
```

Create a file named `debug_bot.py` with the following content:
```python
import sys
from dotenv import load_dotenv

sys.path.append('BenalUMAbot')

import BenalUMAbot.bot as bot
bot.main(False)
```

Last, install the required dependency for this file:
```bash
pip install python-dotenv
```

Finally, start the bot by running `debug_bot.py`.



## Contributing

Contributions are always welcome! You can fork the project and issue a pull request.
You can also directly contact me if you detect bugs or have any idea for improvement.


## Authors

- [Pablo Mateos Ruiz](https://github.com/Pablo097)


## License

[GPL 3.0](https://choosealicense.com/licenses/gpl-3.0/)
