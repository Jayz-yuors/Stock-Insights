from pymongo import MongoClient
import streamlit as st
import os

def create_connection():
    try:
        mongo_url = st.secrets["MONGO_URL"]
        mongo_db = st.secrets["MONGO_DB"]
    except Exception:
        mongo_url = os.getenv("MONGO_URL")
        mongo_db = os.getenv("MONGO_DB", "stocks_db")

    if not mongo_url:
        raise Exception("MongoDB URL not found in secrets or environment variables")

    client = MongoClient(mongo_url)
    db = client[mongo_db]
    return db
