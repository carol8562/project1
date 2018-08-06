import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

db.execute ("CREATE TABLE IF NOT EXISTS books (isbn VARCHAR PRIMARY KEY UNIQUE NOT NULL, title VARCHAR NOT NULL, author VARCHAR NOT NULL, pub_year INTEGER NOT NULL)")
db.commit()

db.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name VARCHAR UNIQUE NOT NULL, password VARCHAR NOT NULL)")
db.commit()

db.execute("CREATE TABLE IF NOT EXISTS reviews (id SERIAL PRIMARY KEY, isbn VARCHAR NOT NULL, userid INTEGER NOT NULL, review VARCHAR NOT NULL, stars INT NOT NULL)")
db.commit()
