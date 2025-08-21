
import psycopg2
from psycopg2 import OperationalError
import streamlit as st

def create_connection():
    connection = None
    try:
        connection = psycopg2.connect(
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_HOST"],
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


import psycopg2
from psycopg2 import OperationalError
def create_connection ():
    connection = None
    try :
        connection = psycopg2.connect(
            dbname = "DemoDb",
            user = "postgres",
            password = "JayK@123!",
            host = "localhost",
            port = "5432"             
            )
        print("Connection to PostgreSQL DB successful")
    except OperationalError as e:
        print(f"The error '{e}' occurred")
    return connection
def close_connection(connection):
    if connection :
        connection.close()
        print("PostGreSQL Connection closed:")

