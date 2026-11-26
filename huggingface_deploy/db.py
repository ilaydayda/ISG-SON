"""MongoDB Atlas bağlantı katmanı.

Bağlantı adresi koda yazılmaz; şu sırayla aranır:
  1) MONGODB_URI ortam değişkeni (Hugging Face Spaces > Settings > Secrets)
  2) .streamlit/secrets.toml içindeki MONGODB_URI (lokal çalıştırma / Streamlit Cloud)
Bulunamazsa veya bağlanılamazsa None döner (uygulama çevrimdışı moda düşer)."""
import os
import pymongo
import certifi

DB_NAME = "KimyaProjesi"
COLLECTION_NAME = "Envanter"


def _get_uri():
    uri = os.environ.get("MONGODB_URI")
    if uri:
        return uri
    try:
        import streamlit as st
        return st.secrets.get("MONGODB_URI")
    except Exception:
        return None


def get_collection():
    """Envanter koleksiyonuna bağlanır. Bağlantı kurulamazsa None döner."""
    uri = _get_uri()
    if not uri:
        return None
    try:
        client = pymongo.MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
        client.admin.command('ping')
        return client[DB_NAME][COLLECTION_NAME]
    except Exception:
        return None
