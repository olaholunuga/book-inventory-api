from models.book import Book
from models.author import Author
from models.category import Category
from models.publisher import Publisher
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from os import getenv
from models.base_model import Base
from dotenv import load_dotenv


load_dotenv()
# Map model names for easy querying
classes = {
    "Book": Book,
    "Author": Author,
    "Category": Category,
    "Publisher": Publisher,
}

class DBStorage:
    __engine = None
    __session = None

    def __init__(self):
        """Initialize engine based on environment"""
        ENV = getenv("APP_ENV", "dev")

        if ENV == "dev":
            # SQLite for development
            self.__engine = create_engine("sqlite:///book-store.db", echo=True)
        else:
            # PostgreSQL / MySQL for production (DATABASE_URL should be like: postgresql://user:pass@host/dbname)
            DATABASE_URL = getenv("DATABASE_URL")
            self.__engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    def reload(self):
        """Create tables and start session"""
        Base.metadata.create_all(self.__engine)
        session_factory = sessionmaker(bind=self.__engine, expire_on_commit=False)
        Session = scoped_session(session_factory)
        self.__session = Session

    def all(self, cls=None):
        """Query objects"""
        obj_dict = {}
        if cls:
            objs = self.__session.query(cls).all()
        else:
            objs = []
            for model in classes.values():
                objs += self.__session.query(model).all()

        for obj in objs:
            obj_dict[f"{obj.__class__.__name__}.{obj.id}"] = obj
        return obj_dict

    def new(self, obj):
        """Add object to session"""
        self.__session.add(obj)

    def save(self):
        """Commit session"""
        try:
            self.__session.commit()
        except SQLAlchemyError:
            self.__session.rollback()
            raise

    def delete(self, obj=None):
        """Delete object if exists"""
        if obj:
            self.__session.delete(obj)

    def get(self, cls, id):
        """Fetch one object by class and ID"""
        if cls in classes.values():
            return self.__session.query(cls).get(id)
        return None

    def count(self, cls=None):
        """Count objects"""
        if cls:
            return self.__session.query(cls).count()
        total = 0
        for model in classes.values():
            total += self.__session.query(model).count()
        return total

    def close(self):
        """Remove session (for API teardown)"""
        self.__session.remove()