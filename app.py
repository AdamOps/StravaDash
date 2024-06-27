from app_class import *
from dotenv import load_dotenv
import os

load_dotenv('.env')

CLIENT_ID: int = int(os.getenv('CLIENT_ID'))
CLIENT_SECRET: str = os.getenv('CLIENT_SECRET')
REFRESH_TOKEN: str = os.getenv('REFRESH_TOKEN')

if __name__ == '__main__':
    app_instance = DashApp(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
    app_instance.runApp()
