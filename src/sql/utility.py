import os, sqlalchemy, pg8000, discord

from sqlalchemy.orm import sessionmaker, session
from sqlalchemy.ext.declarative import declarative_base
from google.cloud.sql.connector import Connector, IPTypes

from .models import *

######################################################

#######################
# SQL SETUP FUNCTIONS # 
#######################

def connect_with_connector(echo = False) -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of MySQL.
    Uses the Cloud SQL Python Connector package.
    Reference: https://cloud.google.com/sql/docs/mysql/connect-connectors
    """

    # Note: Saving credentials in environment variables is convenient, but not
    # secure - consider a more secure solution such as
    # Cloud Secret Manager (https://cloud.google.com/secret-manager) to help
    # keep secrets safe.

    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]  # e.g. 'project:region:instance'
    db_user = os.environ["DB_USER"]  # e.g. 'my-db-user'
    db_pass = os.environ["DB_PASS"]  # e.g. 'my-db-password'
    db_name = os.environ["DB_NAME"]  # e.g. 'my-database'

    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

    connector = Connector()

    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type=ip_type,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        echo=echo
    )
    return pool

def setup(echo):
    engine = connect_with_connector(echo)
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(bind=engine)
    session.commit()
    return engine, session 

###################
# DB MANIPULATION #
###################

def check_user_registered(session: session.Session, user: discord.member.Member):
    return session.query(User).filter_by(discord_id=user.id).first() is not None

def register_user(session: session.Session, user: discord.member.Member):
    if not check_user_registered(session, user):
        session.add(User(discord_id=user.id))
        session.commit()
        return True
    return False 

def check_bot_registered(session: session.Session, bot: discord.user.ClientUser):
    return session.query(Bot).filter_by(discord_id=bot.id).first() is not None

def register_bot(session: session.Session, bot: discord.user.ClientUser):
    entry = session.query(Bot).filter_by(discord_id=bot.id).first()
    if entry is None:
        session.add(Bot(user=str(bot), username=bot.name, discord_id=bot.id))
        session.commit()
        return True
    # Update to latest username
    if entry is not None and entry.username != bot.name:
        entry.user = str(bot)
        entry.username = bot.name
        session.commit()
        return True
    return False

def check_server_registered(session: session.Session, server: discord.guild.Guild):
    return session.query(Server).filter_by(discord_id=server.id).first() is not None

def register_server(session: session.Session, server: discord.guild.Guild):
    entry = session.query(Server).filter_by(discord_id=server.id).first()
    if entry is None:
        session.add(Server(name=server.name, discord_id=server.id))
        session.commit()
        return True
    # Update to latest servername
    if entry is not None and entry.name != server.name:
        entry.name = server.name
        session.commit()
        return True
    return False 

def check_channel_registered(session: session.Session, channel: discord.channel.TextChannel):
    return session.query(Server).filter_by(channel_id=channel.id).first() is not None

def register_channel(session: session.Session, server: discord.guild.Guild, channel: discord.channel.TextChannel):
    entry = session.query(Server).filter_by(channel_id=channel.id).first()
    if entry is None:
        session.add(Server(name=server.name, discord_id=server.id, channel_id=channel.id))
        session.commit()
        return True
    # Update to latest servername
    if entry is not None and entry.name != server.name:
        entry.name = server.name
        session.commit()
        return True
    return False 

def add_message(session: session.Session, bot: discord.user.ClientUser, channel: discord.channel.TextChannel, sender, message: str):
    try:
        line = ConversationLine(bot=bot.id, channel=channel.id, sender=sender.id, message=message)
        session.add(line)
        session.commit()
        return True

    except Exception as e:
        return False