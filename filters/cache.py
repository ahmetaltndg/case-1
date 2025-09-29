# LRU cache implementation
from collections import OrderedDict
import time

class LRUCache:
    def __init__(self, capacity=100):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache.pop(key)
            # 5 dakika (300 sn) içinde ise cache'den döndür
            if time.time() - timestamp < 300:
                self.cache[key] = (value, timestamp)
                return value
        return None

    def set(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = (value, time.time())

lru_cache = LRUCache()

def cache_get(key):
    return lru_cache.get(key)

def cache_set(key, value):
    lru_cache.set(key, value)
