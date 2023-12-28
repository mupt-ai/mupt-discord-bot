from datetime import datetime

from sqlalchemy     import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Model definitions
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, discord_id={self.discord_id!r})"

class Bot(Base):
    __tablename__ = 'bots'
    id = Column(Integer, primary_key=True)
    user = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    discord_id = Column(BigInteger, nullable=False, unique=True)

    def __repr__(self) -> str:
        return (f"Bot(id={self.id!r}, user={self.user!r}, "
                f"username={self.username!r}, discord_id={self.discord_id!r})")

class Server(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    discord_id = Column(BigInteger, nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"Server(id={self.id!r}, name={self.name!r}, discord_id={self.discord_id!r})"

class ConversationLine(Base):
    __tablename__ = 'conversation_lines'
    id = Column(Integer, primary_key=True)
    bot = Column(BigInteger, ForeignKey('bots.discord_id'))
    server = Column(BigInteger, ForeignKey('servers.discord_id'))
    sender = Column(BigInteger, nullable=False)
    message = Column(String(2048), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"ConversationLine("
            f"id={self.id!r}, server={self.server!r}, "
            f"bot={self.bot!r}, sender={self.sender!r}, "
            f"message={self.message!r}, timestamp={self.timestamp!r})"
        )