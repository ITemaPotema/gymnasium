from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from database import *
import vk_api
from decouple import config
from shemas import UserVkData, TokenRequest, IphoneUser
from app_config import auth, logger, verify_signature, verify_init_data, get_user_id




auth_router = APIRouter()

templates = Jinja2Templates(directory="templates")


@auth_router.get("/auth_vk")
def empty_auth(request: Request):
    user_system = request.headers.get("User-Agent")
    logger.error(f"Redirect error. User {user_system } was redirected on page he shoudn`t during VK authorization")

    context = {
        "request": request,
        "message": "Ошибка! Не удалось авторизоваться!",
        "comment": "Возможно проблема в ОС Вашего устройства. Если Вы сейчас заходите с IPhone укажите IOS в начальном диалоге авторизации!"
    }

    return templates.TemplateResponse("finish_authorization.html", context=context)

@auth_router.get("/welcome_authorization")
def welcome_to_authorization(request: Request):
    user_system = request.headers.get("User-Agent")

    logger.info(f"client: {request.client.host}:{request.client.port}")
    logger.info(f"Start login process by {user_system}")
    return templates.TemplateResponse("welcome_authorization.html", {"request": request})


@auth_router.get("/authorization")
def authorize_with_vk(request: Request):
    return templates.TemplateResponse("authorization.html", {"request": request})


@auth_router.get("/finish_authorization")
def answer_with_success(request: Request, status: int):
    user_system = request.headers.get("User-Agent")

    context = {
        "request": request,
        "message": None,
        "comment": None
    }

    if status == 201:
        context["message"] = "Такой пользователь уже авторизован!"
        context["comment"] = "Вернитесь в бота и создайте свой личный профиль, если Вы ещё этого не сделали(/personal)."
        logger.info("User is already authorized")

    elif status == 200:
        context["message"] = "Поздравляем! Авторизация прошла успешно!"
        context["comment"] = "Вернитесь в бота и создайте свой личный профиль(/personal)"
        logger.info(f"Succesful authorization by {user_system}")

    elif status == 400:
        context["message"] = "Ошибка! Не удалось авторизоваться!"
        context["comment"] = "Попробуйте ещё раз!"
        logger.error(f"Authorization error by {user_system}")

    return templates.TemplateResponse("finish_authorization.html", context=context)

@auth_router.post("/auth_iphone")
def auth_iphone(request: Request, data: IphoneUser, db: Session = Depends(get_db)):
    user_id = data.tg_id
    signature = request.headers.get("x-signature")

    if not verify_signature(str(user_id), signature):
        return JSONResponse(content={"error": "no matches in signature comparison"}, status_code=400)

    user_exist = db.query(UsersPersonal).filter_by(tg_id=user_id).first()

    if user_exist:
        return JSONResponse({"message": "user already exists"}, status_code=201)

    try:
        vk_session = vk_api.VkApi(token=config("VK_TOKEN"))
        vk = vk_session.get_api()
        user = vk.users.get(user_ids=data.vk_id, fields='first_name, last_name, sex', lang="ru")[0]

        data = {
            "tg_id": data.tg_id,
            "vk_id": data.vk_id,
            "tg_name": data.tg_name,
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "sex": user["sex"],
        }

        new_pupil = UsersPersonal(**data)
        db.add(new_pupil)
        db.commit()
        print("Добавлен новый ученик")

        return JSONResponse({"message": "ok"}, status_code=200)

    except Exception as e:
        print(e)
        return JSONResponse({"status": "VK api error"}, status_code=400)

@auth_router.post("/auth")
def verify_user_with_vk_id(user_data: UserVkData, db: Session = Depends(get_db)):
    access_token, vk_id, tg_name, init_data = user_data.access_token, user_data.vk_id, user_data.tg_name, user_data.init_data
    tg_id = get_user_id(init_data)

    if not verify_init_data(init_data):
        return JSONResponse(content={"error": "no verified user"}, status_code=401)

    user_exist = db.query(UsersPersonal).filter_by(tg_id=tg_id).first()

    if user_exist:
        return JSONResponse({"message": "user already exists"}, status_code=201)

    try:
        vk_session = vk_api.VkApi(token=access_token)
        vk = vk_session.get_api()
        user = vk.users.get(fields='first_name, last_name, sex', lang="ru")[0]
        print("Авторизация через токен")

    except Exception as e:
        print(e)
        try:
            vk_session = vk_api.VkApi(token=config("VK_TOKEN"))
            vk = vk_session.get_api()
            user = vk.users.get(user_ids=vk_id, fields='first_name, last_name, sex', lang="ru")[0]
            print("Авторизация через id")

        except Exception as e:
            print(e)
            return JSONResponse({"status": "VK api error"}, status_code=400)

    data = {
        "tg_id": tg_id,
        "vk_id": vk_id,
        "tg_name": tg_name,
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "sex": user["sex"],
    }

    new_pupil = UsersPersonal(**data)
    db.add(new_pupil)
    db.commit()
    print("Добавлен новый ученик")

    return JSONResponse({"message": "ok"}, status_code=200)


@auth_router.post("/sign_in")
def get_access_token(request: Request, data: TokenRequest, db: Session = Depends(get_db)):
    user_id = data.user_id
    signature = request.headers.get("x-signature")

    if not verify_signature(str(user_id), signature):
        return JSONResponse(content={"error": "no matches in signature comparison"}, status_code=400)

    profile = db.query(UsersGeneral).filter_by(tg_id=user_id).first()

    if not profile:
        return JSONResponse(content={"error": "has no profile"}, status_code=404)

    is_admin = bool(profile.is_admin)
    access_token = auth.create_access_token(uid=str(user_id), data={"adm": is_admin})

    return JSONResponse(content={"access_token": access_token, "is_admin": is_admin})

