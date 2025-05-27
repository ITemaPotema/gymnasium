from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import update
from database import *
from app_config import auth, verify_init_data, get_user_id, check_query_id_unique, verify_signature
from authx import TokenPayload
from shemas import Balance


gymcoin_router = APIRouter()

templates = Jinja2Templates(directory="templates")

@gymcoin_router.get("/gymcoins")
def tap_gymcoin_view(request: Request):
    return templates.TemplateResponse("tap_gymcoin.html", context={"request": request})


@gymcoin_router.get("/user/balance")
def get_user_balance(payload: TokenPayload = Depends(auth.access_token_required), db: Session = Depends(get_db)):
    user_id = int(payload.sub)
    balance = db.query(Wallet.balance).filter_by(wallet_id=user_id).first()[0]

    if balance is None:
        return JSONResponse({"error": "user not found"}, status_code=404)

    return JSONResponse({"balance": balance})


@gymcoin_router.post("/gymcoins/save")
def save_gymcoins(data: Balance,  db: Session = Depends(get_db)):
    balance = data.balance
    init_data = data.init_data
    user_id = get_user_id(init_data)

    if not verify_init_data(init_data):
        return JSONResponse(content={"error": "invalid params"}, status_code=400)

    if balance > 10000: # если вывод подозрительно большой
        return JSONResponse(content={"error": "user is not verified"}, status_code=403)

    user_exist = db.query(UsersPersonal).filter_by(tg_id=user_id).first()

    if not user_exist:
        return JSONResponse({"error": "user not found"}, status_code=404)

    stmt = (
        update(Wallet)
        .filter_by(wallet_id=user_id)
        .values(balance=Wallet.balance + balance)
    )

    db.execute(stmt)
    db.commit()

    return {"status": "ok"}


@gymcoin_router.post("/gymcoins/withdraw")
def withdraw_funds(query: str, funds_amount: int, db: Session = Depends(get_db),
                   payload: TokenPayload = Depends(auth.access_token_required),
                   ):

    query_id, time_stamp = query.split(":")
    user_id = int(payload.sub)

    if not verify_signature(str(user_id), query_id): # проверка query_id на подлинность
        return JSONResponse(content={"error": "no matches in signature comparison"}, status_code=400)

    if not check_query_id_unique(query_id, int(time_stamp)): # проверка query_id на одноразовость
        return JSONResponse(content={"error": "query is not valid"}, status_code=400)

    user_id = int(payload.sub)

    stmt = update(Wallet).filter_by(wallet_id=user_id).values(balance=Wallet.balance + funds_amount)

    db.execute(stmt)
    db.commit()

    return JSONResponse(content={"status": "ok"})
