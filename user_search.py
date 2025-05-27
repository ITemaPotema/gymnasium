from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, update, func
from database import *
from app_config import auth, all_forms
from authx import TokenPayload


search_router = APIRouter()


@search_router.get("/users/form/{form}", dependencies=[Depends(auth.access_token_required)])
def get_pupils_from_db(form: str, db: Session = Depends(get_db)):
    data_all = db.query(UsersGeneral).filter_by(form=form).all()
    data = dict()

    for pupil in data_all:

        pupil_data = dict()

        pupil_data["tg_id"] = pupil.tg_id
        pupil_data["first_name"] = pupil.personal_info.first_name
        pupil_data["last_name"] = pupil.personal_info.last_name
        pupil_data["tg_name"] = pupil.personal_info.tg_name
        pupil_data["photo"] = pupil.photo
        pupil_data["info"] = pupil.info
        pupil_data["karma"] = pupil.karma
        pupil_data["is_admin"] = pupil.is_admin

        data[pupil.tg_id] = pupil_data

    return JSONResponse(content=data)



@search_router.get("/users/feed")
def get_user_feed(form_min: int, sex: list[int] = Query(), db: Session = Depends(get_db),
                  payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = int(payload.sub)

    need_forms = [form for form in all_forms if int(form[:len(form)-1]) >= form_min]
    stmt = and_(

                    UsersGeneral.form.in_(need_forms),
                    UsersPersonal.sex.in_(sex),
                )


    LIMIT = 10

    result = (
        db.query(UsersPersonal)
        .join(UsersGeneral)
        .filter(stmt)
        .order_by(func.random())
        .limit(LIMIT)
        .all())

    data_response = []

    for personal in result:
        pupil_data = {}
        general_data = personal.general_info

        pupil_data["tg_id"] = personal.tg_id
        pupil_data["first_name"] = personal.first_name
        pupil_data["last_name"] = personal.last_name
        pupil_data["form"] = general_data.form
        pupil_data["tg_name"] = personal.tg_name
        pupil_data["photo"] = general_data.photo
        pupil_data["info"] = general_data.info
        pupil_data["karma"] = general_data.karma

        data_response.append(pupil_data)

    return JSONResponse(content=data_response)


@search_router.post("/like", dependencies=[Depends(auth.access_token_required)])
def like_user(tg_id: int, db: Session = Depends(get_db)):
    stmt = (
        update(UsersGeneral)
        .filter_by(tg_id=tg_id)
        .values(karma=UsersGeneral.karma + 1)
    )

    db.execute(stmt)
    db.commit()

    return JSONResponse(content={"status": "ok"})





