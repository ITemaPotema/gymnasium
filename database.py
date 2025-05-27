from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import create_engine, Column, ForeignKey, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from decouple import config

engine = create_engine(config("DB_URL"), connect_args={"check_same_thread": False})
class Base(DeclarativeBase): pass

SessionLocal = sessionmaker(bind=engine)

def get_db():
    with SessionLocal() as session:
        yield session


class UsersPersonal(Base):
    __tablename__ = "personals"

    tg_id: Mapped[int] = mapped_column(primary_key=True)
    vk_id: Mapped[int]
    tg_name: Mapped[str]
    first_name: Mapped[str]
    last_name: Mapped[str]
    sex: Mapped[int]

    general_info: Mapped["UsersGeneral"] = relationship(
        back_populates="personal_info",
        cascade="all, delete"
    )


class UsersGeneral(Base):
    __tablename__ = "generals"

    tg_id: Mapped[int] = mapped_column(
        ForeignKey("personals.tg_id", ondelete="CASCADE"),
        primary_key=True
    )
    photo: Mapped[str]
    info = Column(Text)
    karma: Mapped[int] = mapped_column(default=0)
    form: Mapped[str]
    is_admin: Mapped[int]

    personal_info: Mapped["UsersPersonal"] = relationship(
        back_populates="general_info",
    )

    posts: Mapped[list["Posts"]] = relationship(
        back_populates="user_general",
        cascade="all, delete",
    )

    wallet_info: Mapped["Wallet"] = relationship(
        back_populates="general_info",
        cascade="all, delete"
    )


class Posts(Base):
    __tablename__ = "posts"

    post_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    time_create = Column(DateTime)
    text: Mapped[str] = mapped_column(nullable=True)
    content: Mapped[str] = mapped_column(nullable=True)
    likes: Mapped[int] = mapped_column(default=0)
    dislikes: Mapped[int] = mapped_column(default=0)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("generals.tg_id", ondelete="CASCADE")
    )
    describe: Mapped[str]
    type: Mapped[str]
    toxicity: Mapped[str] = mapped_column(nullable=True)

    user_general: Mapped["UsersGeneral"] = relationship(
        back_populates="posts",
    )


class Wallet(Base):
    __tablename__ = "wallet"

    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("generals.tg_id", ondelete="CASCADE"),
        primary_key=True
    )
    balance: Mapped[int] = mapped_column(default=0)

    general_info: Mapped["UsersGeneral"] = relationship(
        back_populates="wallet_info",
    )








