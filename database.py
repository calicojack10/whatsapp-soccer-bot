from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///users.db")

Session = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    phone = Column(String, primary_key=True)
    auto_updates = Column(Boolean, default=False)


Base.metadata.create_all(engine)