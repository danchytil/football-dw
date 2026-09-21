import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Creates connection to Postres SQL database"""
    
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "football_dw")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")

    if not user or not password:
        raise ValueError("Missing DB_USER or DB_PASS in .env!")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )