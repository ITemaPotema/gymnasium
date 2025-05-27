from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
from database import *
from auth import auth_router
from user_profile import profile_router
from user_search import search_router
from posts_feed import feed_router
from gymcoins import gymcoin_router
from admin import admin_router
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
            "http://0.0.0.0:8000",
            "https://gymnazium587-itemapotema.amvera.io",
            "https://telegrambot-itemapotema.amvera.io"
        ],
)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(search_router)
app.include_router(feed_router)
app.include_router(gymcoin_router)
app.include_router(admin_router)




Base.metadata.create_all(bind=engine)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, err: RequestValidationError):
    return JSONResponse({"message": "Некорректный формат данных!"}, status_code=400)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost",
                port=8000,
                )