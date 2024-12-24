import redis
import os
from dotenv import load_dotenv
load_dotenv()
import json

REDIS_SERVER = os.getenv("REDIS_SERVER") or 'localhost'
redis_server = redis.Redis(REDIS_SERVER)
REDIS_EXPIRE_HISTORY_TIME = os.getenv('REDIS_EXPIRE_HISTORY_TIME') or 60*60*8


def saveData(key, value,extime=None):
    if value.get('history'):
        value['history'] = json.dumps(value.get('history', []))
    redis_server.hmset(f"user:{key}", value)
    redis_server.expire(f"user:{key}", extime if extime else REDIS_EXPIRE_HISTORY_TIME)


def getData(key):
    data= redis_server.hgetall(f"user:{key}")
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') if k != b'history' else json.loads(v.decode('utf-8')) for k, v in data.items()}
    return decoded_data


def getField(key, field):
    value = redis_server.hget(f"user:{key}", field)
    if value:
        value = value.decode('utf-8')
        if field == 'history':
            return json.loads(value)
        return value
    return None


def editData(key, field, value):
    if field == 'history':
        value = json.dumps(value)
    redis_server.hset(f"user:{key}", field, value)


def destroyData(key):
    redis_server.delete(f"user:{key}")


def test(key,value):
    saveData(key, value)
    print(getData(key),"user history")
    editData(key, "email", "new.email@example.com")
    editData(key, "history", ['updatedname'])
    print(getData(key),type(getData(key)))
    print(getField(key,"name"))
    
