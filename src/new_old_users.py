import config
from utils import ChatTools, signin

if __name__ == "__main__":
    dog_client = signin(config.BOT_API_ID, config.BOT_API_HASH)

    with dog_client:

        ct = ChatTools(dog_client, config.MAIN_CHAT_ID)
        ct.find_db_users_not_in_chat()
        ct.find_chat_users_not_in_db()
