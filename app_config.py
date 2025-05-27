import json
from decouple import config
from authx import AuthXConfig, AuthX
from datetime import timedelta
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl
from redis import Redis
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a"
)
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

fh = logging.FileHandler("app.log")
fh.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)

logger.addHandler(fh)


auth_config = AuthXConfig(
        JWT_ALGORITHM = "HS256",
        JWT_SECRET_KEY = config("RANDOM_SECRET"),
        JWT_TOKEN_LOCATION = ["headers"],
        JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=20),
)

auth = AuthX(config=auth_config)

SECRET_KEY = config("SECRET_KEY")

def verify_signature(data: str, signature: str) -> bool:
    expected_signature = hmac.new(
        SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


BOT_TOKEN = config("BOT_TOKEN")
REDIS_DOMAIN = config("REDIS_DOMAIN")
REDIS_PASSWORD = config("REDIS_PASSWORD")

def get_redis():
    return Redis(host=REDIS_DOMAIN, password=REDIS_PASSWORD, port=6379, db=1)

def get_user_id(init_data: str):
    parsed_data = dict(parse_qsl(init_data))
    user_json = parsed_data.get("user", "{}")

    user_data = json.loads(user_json)
    user_id = int(user_data.get("id"))

    return user_id


# проверка на одноразовость query_id
def check_query_id_unique(query_id: str, time_stamp: int, n: int = None):
    redis = get_redis()

    if n:
        query_id = query_id[:n] # сокращаем query id, так как он может быть очень длинным(hmac)

    time_delta = int(time.time()) - time_stamp
    if time_delta > 60 * 15:  # проверка, что запрос не старый (15 мин)
        return False

    print(f"time_delta: {time_delta}", f"query_id={query_id}")

    if redis.get(f"used_query_id:{query_id}"):  # проверка того, что данный query_id не был в недавних запросах
        return False

    redis.setex(f"used_query_id:{query_id}", 60 * 15, query_id)  # сохраняем query_id на 15 мин

    return True


def verify_init_data(init_data: str):
    parsed_data = dict(parse_qsl(init_data))
    hash_str = parsed_data.pop("hash", None)
    query_id = parsed_data.get("query_id")
    auth_date = parsed_data.get("auth_date")

    if not hash_str or not query_id or not auth_date:
        return False

    # Сортируем параметры и формируем строку для проверки
    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(parsed_data.items())
    )

    # Вычисляем HMAC-SHA-256
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode(),
        digestmod=hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    # сверяем хэши
    if computed_hash == hash_str:
        return check_query_id_unique(query_id, int(auth_date))

    return False


all_forms = [
    "6А", "6Б", "6В", "6Г",
    "7А", "7Б", "7В", "7Г", "7Д",
    "8А", "8Б", "8В", "8Д",
    "9А", "9Б", "9В", "9Г",
    "10А", "10Б", "10В", "10Г",
    "11А", "11Б"
]