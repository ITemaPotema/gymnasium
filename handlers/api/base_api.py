from decouple import config
import hashlib
import hmac



redis_domain = "localhost" #config("REDIS_DOMAIN")
redis_password = None # config("REDIS_PASSWORD")
app_url = "http://localhost:8000" # config("APP_URL")
SECRET_KEY = config("SECRET_KEY")


class BaseApi:
    redis_url = f"redis://{redis_domain}:6379/0"
    redis_password = redis_password
    app_url = app_url
    secret_key = SECRET_KEY

    def __init__(self, tg_id):
        self.tg_id = tg_id


    @classmethod
    def generate_signature(cls, data, secret_key):
        data = str(data)
        signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature