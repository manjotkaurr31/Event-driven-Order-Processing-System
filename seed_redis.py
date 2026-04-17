import redis

redis_client = redis.Redis.from_url(os.environ.get("REDIS_CONNECTION"))
inventory = {
    "printer": 3,
    "mouse": 5,
    "cpu": 2,
    "headset": 4,
    "mousepad": 6,
    "charger": 5,
    "keyboard": 3,
    "microphone": 2,
    "scanner": 1
}

for item, stock in inventory.items():
    redis_client.set(f"stock:{item}", stock)

print("Inventory seeded successfully!")