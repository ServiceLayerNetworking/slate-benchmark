from fastapi import FastAPI, Query
from collections import OrderedDict
import os
import threading
import time

app = FastAPI()

CACHE_SIZE = int(os.getenv("CACHE_SIZE", "100"))
DB_LATENCY_MS = int(os.getenv("DB_LATENCY_MS", "100"))

cache = OrderedDict()
lock = threading.Lock()

@app.get("/getRecord")
def get_record(record_id: str = Query(...)):
    with lock:
        if record_id in cache:
            cache.move_to_end(record_id)
            return {"source": "cache", "record_id": record_id}
        
        time.sleep(DB_LATENCY_MS / 1000.0)
        
        if len(cache) >= CACHE_SIZE:
            cache.popitem(last=False)
        cache[record_id] = True
        return {"source": "db", "record_id": record_id}


@app.post("/setRecord")
def set_record(record_id: str = Query(...)):
    with lock:
        if len(cache) >= CACHE_SIZE:
            cache.popitem(last=False)
        cache[record_id] = True
    return {"status": "ok", "record_id": record_id}
