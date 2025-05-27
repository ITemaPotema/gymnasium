from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, update, delete, func
from database import *
from app_config import auth
from shemas import Post, PostCreate, PostStat, Likers
from datetime import datetime, timedelta
from authx import TokenPayload
import requests

feed_router = APIRouter()

ML_URL = config("ML_URL")
ML_API_TOKEN = config("ML_API_TOKEN")

def check_and_insert_toxicity(post_id: int, post_text: str):
    headers = {"Authorization": f"Bearer {ML_API_TOKEN}"}
    data = {"inputs": post_text}

    response = requests.post(ML_URL, headers=headers, json=data)

    if response.status_code == 200:
        toxicity_data = response.json()

        toxicity_label = toxicity_data[0][0]["label"] # метка токсичности

        db: Session = next(get_db()) # объект бд сессии

        stmt = update(Posts).filter_by(post_id=post_id).values(toxicity=toxicity_label)

        db.execute(stmt)
        db.commit()



@feed_router.post("/post/create")
async def create_post(data: PostCreate,
                      background_tasks: BackgroundTasks,
                      payload: TokenPayload = Depends(auth.access_token_required),
                      db: Session = Depends(get_db)):

    tg_id = int(payload.sub)
    time_create = datetime.now()

    post = Posts(time_create=time_create, text=data.text, content=data.content, creator_id=tg_id,
                 describe=data.describe, type=data.type)

    db.add(post)
    db.commit()

    # задача в отдельном потоке по проверке токсичности текста
    if post.text:
        background_tasks.add_task(
            check_and_insert_toxicity,
            post.post_id,
            post.text
        )

    return JSONResponse(content={"status": "ok"})


@feed_router.get("/post/feed", dependencies=[Depends(auth.access_token_required)])
def get_post_feed(only_negative: int = 0, db: Session = Depends(get_db)):
    LIMIT = 10

    stmt = delete(Posts).filter(Posts.time_create < datetime.now() - timedelta(days=1)) # удаляем старые посты
    db.execute(stmt)
    db.commit()

    if only_negative:
        negative_labels = ["insult", "dangerous", "obscenity", "threat"]
        posts = db.query(Posts).filter(Posts.toxicity.in_(negative_labels)).order_by(func.random()).limit(LIMIT).all()

    else:
        posts = db.query(Posts).order_by(func.random()).limit(LIMIT).all() # скачиваем из бд LIMIT кол во постов

    if not posts:
        return JSONResponse(content={"message": "no posts"}, status_code=404)

    posts_json = []

    for post in posts:
        post_data = dict(Post.model_validate(post, from_attributes=True))
        posts_json.append(post_data)

    return JSONResponse(content=posts_json)


@feed_router.get("/post/stat")
def get_my_active_posts(db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = int(payload.sub)

    posts = db.query(Posts).filter_by(creator_id=user_id).all()

    if not posts:
        return JSONResponse(content={"count": 0, "posts": []})

    answer = []
    count = 0

    for post in posts:
        post_data = dict(PostStat.model_validate(post, from_attributes=True))
        answer.append(post_data)
        count += 1

    return JSONResponse(content={"count": count, "posts": answer})

# лайк или дизлайк посту
@feed_router.post("/post/reaction/{action}/{post_id}", dependencies=[Depends(auth.access_token_required)])
def like_post(action: str, post_id: int, db: Session = Depends(get_db)):
    row_exist = db.query(Posts).filter_by(post_id=post_id).first()

    if not row_exist:
        return JSONResponse(content={"error": "post does not exist"}, status_code=404)

    if action == "like":
        stmt = update(Posts).filter_by(post_id=post_id).values(likes=Posts.likes + 1)

    else:
        stmt = update(Posts).filter_by(post_id=post_id).values(dislikes=Posts.dislikes + 1)

    db.execute(stmt)
    db.commit()

    return JSONResponse(content={"status": "ok"})


@feed_router.post("/post/pay")
def pay_for_post(db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    user_id = int(payload.sub)
    post_cost = int(config("POST_COST_CREATE"))

    user_wallet = db.query(Wallet).filter_by(wallet_id=user_id).first()

    if user_wallet.balance < post_cost:
        return JSONResponse({"error": "insufficient funds", "amount": post_cost-user_wallet.balance}, status_code=400)

    user_wallet.balance -= post_cost
    db.commit()

    print(f"Пользователь заплатил {post_cost}")
    return JSONResponse(content={"paid": post_cost})


# выплаты самым популярным постам
@feed_router.get("/post/winners")
def get_most_popular_posts(payload: TokenPayload = Depends(auth.access_token_required), db: Session = Depends(get_db)):
    is_admin = getattr(payload, "adm") # проверка на админа

    if not is_admin:
        return JSONResponse(content={"error": "forbidden action"}, status_code=400)

    top_posts = db.query(Posts).filter(Posts.likes != 0).order_by(desc(Posts.likes), desc(Posts.post_id)).limit(5).all()

    if not top_posts:
        return JSONResponse(content={"error": "posts not found"}, status_code=404)

    amounts = [1000, 800, 700, 600, 500]
    users_fractions = {}

    for i in range(len(top_posts)):
        post = top_posts[i]
        prize = amounts[i]
        creator_wallet = post.user_general.wallet_info


        if users_fractions.get(creator_wallet.wallet_id):
            user_id = creator_wallet.wallet_id
            users_fractions[user_id]["prize"] += prize
            users_fractions[user_id]["places"][i+1] = {"describe": post.describe, "likes": post.likes}

        else:
            users_fractions[creator_wallet.wallet_id] = {
                "prize": prize, "places":
                    {
                        i+1:
                            {
                                "describe": post.describe,
                                "likes": post.likes
                            }
                    }
            }

    amount_sent = int(config("WIN_PAY"))

    return JSONResponse(content={"status": "ok", "amount_sent": amount_sent, "users_fractions": users_fractions})


# получение данных тех, кто лайкнул пост
@feed_router.post("/post/likers/data", dependencies=[Depends(auth.access_token_required)])
def get_likers_data(data: Likers, db: Session = Depends(get_db)):
    data = db.query(UsersPersonal).filter(UsersPersonal.tg_id.in_(data.likers)).all()

    answer = []

    for pupil in data:
        pupil_data = {
            "first_name": pupil.first_name,
            "last_name": pupil.last_name,
            "form": pupil.general_info.form
        }
        answer.append(pupil_data)

    return JSONResponse(content={"data": answer})


@feed_router.delete("/post/delete")
def delete_post(post_id: int, db: Session = Depends(get_db), payload: TokenPayload = Depends(auth.access_token_required)):
    is_admin = getattr(payload, "adm")
    user_id = int(payload.sub)

    if not is_admin:
        stmt = delete(Posts).filter_by(post_id=post_id, creator_id=user_id) # важно, чтоб пост, который собирается удалить пользователь принадлежал именно ему
    else:
        stmt = delete(Posts).filter_by(post_id=post_id) # если пользователь админ, то необязательно, чтоб пост принадлежал именно ему

    result = db.execute(stmt)
    db.commit()

    if result.rowcount == 0:
        return JSONResponse(content={"error": "post not found"}, status_code=404)

    return JSONResponse(content={"status": "ok"})