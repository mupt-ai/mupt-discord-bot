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
    """
    Check if a Discord user is registered in the database.

    Args:
        session (session.Session): The database session.
        user (discord.member.Member): The Discord user to check.

    Returns:
        bool: True if the user is registered, False otherwise.
    """
    return session.query(User).filter_by(discord_id=user.id).first() is not None

def register_user(session: session.Session, user: discord.member.Member):
    """
    Register a new Discord user in the database if not already registered.

    Args:
        session (session.Session): The database session.
        user (discord.member.Member): The Discord user to register.

    Returns:
        bool: True if the user was newly registered, False if already registered.
    """
    if not check_user_registered(session, user):
        session.add(User(discord_id=user.id))
        session.commit()
        return True
    return False 

def check_bot_registered(session: session.Session, bot: discord.user.ClientUser):
    """
    Check if a Discord bot is registered in the database.

    Args:
        session (session.Session): The database session.
        bot (discord.user.ClientUser): The Discord bot to check.

    Returns:
        bool: True if the bot is registered, False otherwise.
    """
    return session.query(Bot).filter_by(discord_id=bot.id).first() is not None

def register_bot(session: session.Session, bot: discord.user.ClientUser):
    """
    Register a new Discord bot in the database or update its information (user string and username) if already registered.

    Args:
        session (session.Session): The database session.
        bot (discord.user.ClientUser): The Discord bot to register or update.

    Returns:
        bool: True if the bot was newly registered or its information was updated, False otherwise.
    """
    entry = session.query(Bot).filter_by(discord_id=bot.id).first()
    if entry is None:
        session.add(Bot(user=str(bot), username=bot.name, discord_id=bot.id))
        session.commit()
        return True
    # Check if need to update to latest username
    if entry.username != bot.name:
        entry.user = str(bot)
        entry.username = bot.name
        session.commit()
        return True
    return False

def check_server_registered(session: session.Session, server: discord.guild.Guild):
    """
    Check if a Discord server is registered in the database.

    Args:
        session (session.Session): The database session.
        server (discord.guild.Guild): The Discord server to check.

    Returns:
        bool: True if the server is registered, False otherwise.
    """
    return session.query(Server).filter_by(discord_id=server.id).first() is not None

def register_server(session: session.Session, server: discord.guild.Guild):
    """
    Register a new Discord server in the database or update its information if already registered.

    Args:
        session (session.Session): The database session.
        server (discord.guild.Guild): The Discord server to register or update.

    Returns:
        bool: True if the server was newly registered or its information was updated, False otherwise.
    """
    entry = session.query(Server).filter_by(discord_id=server.id).first()
    if entry is None:
        session.add(Server(name=server.name, discord_id=server.id))
        session.commit()
        return True
    # Check if need to update to latest servername
    if entry.name != server.name:
        entry.name = server.name
        session.commit()
        return True
    return False 

def check_channel_registered(session: session.Session, channel: discord.channel.TextChannel):
    """
    Check if a Discord channel is registered in the database.

    This function checks if there's a Server entry in the database with a matching channel_id.
    Note that this checks the Server table, not a separate Channel table.

    Args:
        session (session.Session): The database session.
        channel (discord.channel.TextChannel): The Discord channel to check.

    Returns:
        bool: True if a server with this channel_id is registered, False otherwise.
    """
    return session.query(Server).filter_by(channel_id=channel.id).first() is not None

def register_channel(session: session.Session, server: discord.guild.Guild, channel: discord.channel.TextChannel):
    """
    Register a new Discord channel in the database or update server information if the channel is already registered.

    This function adds a new Server entry with the given channel_id if it doesn't exist,
    or updates the server name if the channel is already registered but the server name has changed.

    Args:
        session (session.Session): The database session.
        server (discord.guild.Guild): The Discord server associated with the channel.
        channel (discord.channel.TextChannel): The Discord channel to register.

    Returns:
        bool: True if a new entry was added or an existing entry was updated, False if no changes were needed.
    """
    entry = session.query(Server).filter_by(channel_id=channel.id).first()
    if entry is None:
        session.add(Server(name=server.name, discord_id=server.id, channel_id=channel.id))
        session.commit()
        return True
    # Check if need to update to latest servername
    if entry.name != server.name:
        entry.name = server.name
        session.commit()
        return True
    return False 

def add_message(session: session.Session, bot: discord.user.ClientUser, channel: discord.channel.TextChannel, sender, message: str):
    """
    Add a new message to the conversation log in the database.

    This function creates a new ConversationLine entry with the provided message details
    and adds it to the database.

    Args:
        session (session.Session): The database session.
        bot (discord.user.ClientUser): The Discord bot associated with the message.
        channel (discord.channel.TextChannel): The Discord channel where the message was sent.
        sender: The entity (user or bot) that sent the message. Should have an 'id' attribute.
        message (str): The content of the message.

    Returns:
        bool: True if the message was successfully added to the database, False if an error occurred.

    Note:
        This function silently catches all exceptions and returns False in case of any error.
        Consider adding logging for better error tracking.
    """
    try:
        line = ConversationLine(bot=bot.id, channel=channel.id, sender=sender.id, message=message)
        session.add(line)
        session.commit()
        return True

    except Exception as e:
        # Consider adding logging here, e.g.:
        # logging.error(f"Error adding message to database: {str(e)}")
        return False