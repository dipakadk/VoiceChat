import os
import json
from redis import Redis
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
REDIS_SERVER = os.getenv('REDIS_SERVER') or 'localhost'
redis_server = Redis(REDIS_SERVER)
cache = Redis(REDIS_SERVER)


def setData(request_id, request_data):
    value = json.dumps(request_data)
    cache.set(request_id, value)
    cache.expire(request_id, 60*10)
    
def getData(request_id):
    value=cache.get(request_id)
    if value is not None:
        return json.loads(value)
    return None

def deleteData(request_id):
    cache.delete(request_id)
    
def flushAll():
    cache.flushall()
