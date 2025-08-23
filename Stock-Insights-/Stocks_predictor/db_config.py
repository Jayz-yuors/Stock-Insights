from pymongo import MongoClient
import streamlit as st

def create_connection():
    # Connect using the MongoDB connection string from Streamlit secrets.
    client = MongoClient(st.secrets["MONGO_URL"])
    db_name = st.secrets.get("MONGO_DB", "stocks_db")  # fallback if not set
    db = client[db_name]
    return db

def close_connection(_):
    # No explicit close needed for MongoDB client connections.
    pass
