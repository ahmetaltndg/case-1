import time

# Rate limiter implementation
RATE_LIMIT_WINDOW = 60  # saniye
RATE_LIMIT_MAX = 10     # kullanıcı başına max istek
rate_limit_store = {}

def rate_limiter(user_id: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    if user_id not in rate_limit_store:
        rate_limit_store[user_id] = []
    # Geçerli pencere içindeki istekleri filtrele
    rate_limit_store[user_id] = [t for t in rate_limit_store[user_id] if t > window_start]
    if len(rate_limit_store[user_id]) >= RATE_LIMIT_MAX:
        return False
    rate_limit_store[user_id].append(now)
    return True
