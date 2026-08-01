"""MongoDB Atlas bağlantı katmanı.

Tüm scriptler (Streamlit arayüzü, MSDS içe aktarma script'i) veritabanına
buradan bağlanır; bağlantı bilgisi ve istemci oluşturma mantığı tek yerde
toplanır."""
import pymongo
import certifi

MONGODB_URI = "mongodb+srv://ilaydanyilmaz_db_user:EAtzyxmF1ji6KK1Q@cluster0.ef9qbof.mongodb.net/?appName=Cluster0"
DB_NAME = "KimyaProjesi"
COLLECTION_NAME = "Envanter"


def get_collection():
    """Envanter koleksiyonuna bağlanır. Bağlantı kurulamazsa None döner
    (çağıran taraf çevrimdışı/lokal moda düşer)."""
    try:
        client = pymongo.MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
        client.admin.command('ping')
        return client[DB_NAME][COLLECTION_NAME]
    except Exception:
        return None
