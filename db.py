"""MongoDB Atlas bağlantı katmanı.

Tüm scriptler (Streamlit arayüzü, MSDS içe aktarma script'i) veritabanına
buradan bağlanır; bağlantı bilgisi ve istemci oluşturma mantığı tek yerde
toplanır."""
import os

import certifi
import pymongo
from pymongo.errors import ConfigurationError

# Ortam değişkeni (MONGODB_URI) tanımlıysa o kullanılır, yoksa varsayılan.
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://ilaydanyilmaz_db_user:EAtzyxmF1ji6KK1Q@cluster0.ef9qbof.mongodb.net/?appName=Cluster0",
)
DB_NAME = "KimyaProjesi"
COLLECTION_NAME = "Envanter"

# Son bağlantı hatası (arayüzde gösterilmek üzere)
last_error = None


def _use_public_dns():
    """Windows/modem DNS'i 'mongodb+srv' SRV kaydını çözemediğinde
    Google ve Cloudflare DNS sunucularına geçer."""
    import dns.resolver
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    dns.resolver.default_resolver = resolver


def _connect():
    client = pymongo.MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=8000,
        tlsCAFile=certifi.where(),
    )
    client.admin.command("ping")
    return client[DB_NAME][COLLECTION_NAME]


def get_collection():
    """Envanter koleksiyonuna bağlanır. Bağlantı kurulamazsa None döner
    (çağıran taraf çevrimdışı/lokal moda düşer); hata `last_error`'a yazılır."""
    global last_error
    try:
        try:
            coll = _connect()
        except ConfigurationError:
            # Çoğunlukla SRV DNS sorgusu başarısız -> herkese açık DNS ile tekrar dene
            _use_public_dns()
            coll = _connect()
        last_error = None
        return coll
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        print(f"[db] MongoDB bağlantı hatası -> {last_error}")
        return None


if __name__ == "__main__":
    # Hızlı test:  python db.py
    c = get_collection()
    print("BAĞLANDI ✅" if c is not None else f"BAĞLANAMADI ❌\n{last_error}")
