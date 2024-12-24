from django.db import models




from typing import Annotated

intpk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]

class Base(models.Model):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Blank(Base):
    __tablename__ = 'vetblank'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part: Mapped[str] = mapped_column(String(150), nullable=False)
    questions: Mapped[list['Question']] = relationship("Question", backref="blank")
    # questions: Mapped[list['Question']] = relationship(backref="text1")
    repeatable: Mapped[bool] = mapped_column(BOOLEAN, nullable=False)


class User(Base):
    __tablename__ = 'user'

    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(String(150), nullable=True)
    last_name: Mapped[str] = mapped_column(String(150), nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)


class Question(Base):
    __tablename__ = 'question'

    id: Mapped[intpk]
    text: Mapped[str] = mapped_column(String(150), nullable=True)
    part: Mapped[str] = mapped_column(ForeignKey('vetblank.id', ondelete="CASCADE"))
    type_answer: Mapped[str] = mapped_column(nullable=True)