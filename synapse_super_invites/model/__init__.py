from typing import List
from typing import Optional
from sqlalchemy import ForeignKey, String, Table, Column, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from uuid import uuid4

def uuid_short() -> str:
    return str(uuid.uuid4()).split("-")[0]


class Base(DeclarativeBase):
    pass


token_rooms = Table(
    "token_room_associations",
    Base.metadata,
    Column("token", ForeignKey("tokens.token"), primary_key = True),
    Column("room", ForeignKey("rooms.nameOrAlias"), primary_key = True),
)

class Token(Base):
    __tablename__ = "tokens"
    token: Mapped[str] = mapped_column(
        String(50), default=uuid_short, primary_key=True
    )
    owner: Mapped[str] = mapped_column(String(255))
    create_dm: Mapped[bool] = mapped_column(Boolean)

    rooms: Mapped[List['Room']] = relationship(
        secondary=token_rooms, back_populates="tokens"
    )
    # meta
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now())
    deleted_at = mapped_column(DateTime(timezone=True), default = None)
    
    def __repr__(self) -> str:
        return f"Token({self.token!r}, owned={self.user!r})"

class Room(Base):
    __tablename__ = "rooms"
    nameOrAlias: Mapped[str] = mapped_column(
        String(255), primary_key=True
    )

    tokens: Mapped[List[Token]] = relationship(
        secondary=token_rooms, back_populates="rooms"
    )

    # meta
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now())


class Accepted(Base):
    __tablename__ = "accepted"
    id: Mapped[int] = mapped_column(primary_key=True)
    user: Mapped[str] = mapped_column(String(255))

    token_id = mapped_column(ForeignKey("tokens.token"))
    token = relationship("Token") #, back_populates="accepted")

    # meta
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now())
