from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import update
from database import *
from shemas import UserProfile, EditProfile
from app_config import auth, verify_signature
from authx import TokenPayload

profile_router = APIRouter()

admin_tg_id = config("ADMIN_ID")

@profile_router.post("/profile/create")
def create_profile(request: Request, user: UserProfile, db: Session = Depends(get_db)):
    signature = request.headers.get("x-signature")
    user_id = user.tg_id

    if not verify_signature(str(user_id), signature):
        return JSONResponse({"error": "no matches in signature comparison"}, status_code=400)

    user_authenticated = db.query(UsersPersonal).filter_by(tg_id=user_id).first()

    if not user_authenticated:
        return JSONResponse(content={"error": "user is not authenticated"}, status_code=401)

    is_admin = (str(user_id) == admin_tg_id) # проверка на суперадмина

    data = {
        "tg_id": user_id,
        "photo": user.photo,
        "info": user.info,
        "form": user.form,
        "is_admin": is_admin
    }

    new_profile = UsersGeneral(**data)
    wallet = Wallet(wallet_id=user.tg_id)

    db.add(new_profile)
    db.add(wallet)

    db.commit()

    return JSONResponse({"message": "profile is created successfully"})


@profile_router.get("/profile")
def profile_view(payload: TokenPayload = Depends(auth.access_token_required), db: Session = Depends(get_db)):
    tg_id = int(payload.sub)

    profile = db.query(UsersGeneral).filter_by(tg_id=tg_id).first()

    if profile:
        content = {
            "first_name": profile.personal_info.first_name,
            "last_name": profile.personal_info.last_name,
            "form": profile.form,
            "photo": profile.photo,
            "info": profile.info,
            "karma": profile.karma,
            "is_admin": bool(profile.is_admin)
        }
        return JSONResponse(content=content)

    return JSONResponse({"message": "profile not found"}, status_code=404)


@profile_router.patch("/profile/edit/{category}")
def edit_profile(category: str, edit: EditProfile,  db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = int(payload.sub)

    if category == "photo":
        stmt = update(UsersGeneral).filter_by(tg_id=user_id).values(photo=edit.data)

    else:
        stmt = update(UsersGeneral).filter_by(tg_id=user_id).values(info=edit.data)

    db.execute(stmt)
    db.commit()

    return JSONResponse(content={"status": "ok"})


@profile_router.delete("/profile/deactivate")
def deactivate_profile(db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = int(payload.sub)

    user = db.get(UsersGeneral, user_id)

    if user:
        db.delete(user)
        db.commit()

    return JSONResponse(content={"status": "profile is deleted"})