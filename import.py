import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


engine = create_engine("postgres://qrqzllsppwwrvw:0829a06512dbc8f106a9582941c4902d6d09f596219e3579b6940c5e0a0e7b72@ec2-34-202-88-122.compute-1.amazonaws.com:5432/dc5uvk3kv9kcjd")
# engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": isbn, "title": title, "author": author, "year": year})                                
        print(f"Added {isbn}, {title} , {author}, {year}.")
    db.commit()

if __name__ == "__main__":
    main()
