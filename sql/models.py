from datetime import datetime

from sqlalchemy     import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base


Base = declarative_base()

# Model definitions
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)

class Bot(Base):
    __tablename__ = 'bots'
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    bot_id = Column(Integer, ForeignKey('bots.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)

class ConversationLine(Base):
    __tablename__ = 'conversation_lines'
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    line_number = Column(Integer, nullable=False)
    sender = Column(Integer, nullable=False)
    message = Column(String(2048), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)