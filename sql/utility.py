import os
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pg8000


def connect_with_connector() -> sqlalchemy.engine.base.Engine:
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
        # ...
    )
    return pool

# # Create a new user (replace this with your user identification logic)
# user = User(username='example_user')

# # Use a context manager for the session
# with Session() as session:
#     session.add(user)
#     session.commit()

#     try:
#         all_users = session.query(User).all()

#         # Display user information
#         for user in all_users:
#             print(f"User ID: {user.id}, Username: {user.username}")

#     except Exception as e:
#         print(f"Error fetching data: {e}")
