import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

f = open("books.csv")
reader = csv.reader(f)
for isbn, title, author, pub_year in reader:
    if isbn == 'isbn':
        continue
    try:
        db.execute("INSERT INTO books (isbn, title, author, pub_year) VALUES (:isbn, :title, :author, :pub_year)", {"isbn":isbn, "title":title, "author":author, "pub_year":pub_year})
    except:
        print(f"Error inserting '{ title }' by { author } into database. It is probably already there.")
db.commit()
