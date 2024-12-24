from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

class Settings(BaseModel):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "Gym"

class KeempeSettings(BaseModel):
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "keepMe"

settings = Settings()
kmsettings = KeempeSettings()

kmclient = AsyncIOMotorClient(settings.mongodb_url)
client = AsyncIOMotorClient(settings.mongodb_url)

kmdb = kmclient[settings.database_name]
db = client[settings.database_name]

## keepMe Collections
clients = kmdb["clients"]
branches = kmdb["branches"]

## Gym Collections
vectorstore_info_collection = db["vectorstore_info_collection"]
visitor_leads = db["visitor_leads"]
session_by_email_phone = db["session_by_email_phone"]
visitor_collection = db["visitors"]
messages_collection = db["history"]

session_by_email_phone.create_index("expires_at", expireAfterSeconds=0)

