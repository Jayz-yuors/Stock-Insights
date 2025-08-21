import psycopg2
from psycopg2 import OperationalError
import streamlit as st

def create_connection():
    connection = None
    try:
        connection = psycopg2.connect(
            dbname=st.secrets.get("DB_NAME", "DemoDb"),
            user=st.secrets.get("DB_USER", "postgres"),
            password=st.secrets.get("DB_PASSWORD", "Jay@123!"),
            host=st.secrets.get("DB_HOST", "localhost"),
            port=st.secrets.get("DB_PORT", "5432")
        )
        print("Connection to PostgreSQL DB successful")
    except OperationalError as e:
        print(f"The error '{e}' occurred")
    return connection

def close_connection(connection):
    if connection:
        connection.close()
        print("PostgreSQL connection closed.")
