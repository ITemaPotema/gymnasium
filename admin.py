from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import update
from database import *
from app_config import auth
from shemas import UserID, UserPromotion
from authx import TokenPayload


admin_router = APIRouter()


@admin_router.patch("/admin/user/promotion/{action}") # повысить до админа/удалить из админов
def promote_user_to_admin(action: UserPromotion, data: UserID, db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    is_admin = getattr(payload, "adm")

    if not is_admin:
        return JSONResponse(content={"error": "need admin privileges"}, status_code=403)

    promote_id = data.tg_id

    if action == UserPromotion.UPGRADE:
        stmt = update(UsersGeneral).filter_by(tg_id=promote_id).values(is_admin=1)

    else:
        stmt = update(UsersGeneral).filter_by(tg_id=promote_id).values(is_admin=0)

    db.execute(stmt)
    db.commit()

    return JSONResponse(content={"status": "promoted successfully"})


@admin_router.delete("/admin/user/delete")
def delete_user(data: UserID, db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    is_admin = getattr(payload, "adm")

    if not is_admin:
        return JSONResponse(content={"error": "need admin privileges"}, status_code=403)

    user_id = data.tg_id

    user = db.get(UsersPersonal, user_id)

    if user:
        db.delete(user)
        db.commit()

    return JSONResponse(content={"status": "deleted successfully"})
