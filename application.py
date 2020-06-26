import os

from flask import Flask, session, render_template, request, redirect, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug import secure_filename
import requests, json
from flask import jsonify, make_response
import time

app = Flask(__name__)


KEY = "9oNdkJVy9Lb9lJunOZcq6Q"

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Must provide username")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Must provide password")
            return redirect("/login")
        password = generate_password_hash(request.form.get("password"))
        username = request.form.get("username")
        result = db.execute("SELECT * FROM users WHERE username = :username",{"username": username}).fetchone()
        print(f"Result = {result}")
        if result is None:
            return redirect("/")
        else:
            if check_password_hash(result.password, request.form.get("password")):
                session["username"] = username
                session["name"] = result["name"]
                return redirect("/books")
            else:
                flash("Incorrect username or password.")
                return redirect("/")
    else:
        return render_template("index.html")

@app.route("/books", methods=["GET", "POST"])
def books():
    """Books Main"""
    if request.method == "POST":
        if request.form.get("search"):
            searchby = request.form.get("searchby")
            orderby = request.form.get("searchby")
            search = request.form.get("search")
            if searchby == "title":
                books = db.execute("SELECT * FROM books WHERE title ILIKE :search ORDER by title ASC",
                        {"searchby": f"'searchby'", "search": f"%{search}%"}).fetchall();
            elif searchby == "author":
                books = db.execute("SELECT * FROM books WHERE author ILIKE :search ORDER by author ASC",
                        {"searchby": f"'searchby'", "search": f"%{search}%"}).fetchall();
            elif searchby == "year":
                books = db.execute("SELECT * FROM books WHERE year = :search ORDER by year ASC",
                        {"searchby": f"'searchby'", "search": search}).fetchall();
            else:
                books = db.execute("SELECT * FROM books WHERE isbn LIKE :search ORDER by isbn ASC",
                        {"searchby": f"'searchby'", "search": f"%{search}%"}).fetchall();
            rows = (len(books))
            print(("SELECT * FROM books WHERE :searchby LIKE :search",
                    {"searchby": searchby, "search": f"%{search}%"}))
            print(books)
            return render_template("books.html", books = books, results = rows)
        else:
            return redirect("/books")
    else:
        books = db.execute("SELECT * FROM books ORDER BY isbn ASC LIMIT 10")
        return render_template("books.html", books = books, results = 10)

@app.route("/book_details/<isbn>", methods=["GET", "POST"])
def book_details(isbn):
    result = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn}).json()
    book = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": f"%{isbn}%"}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn ORDER BY date DESC", {"isbn": isbn}).fetchall()
    results = len(reviews)
    user_reviews = db.execute("SELECT * from reviews WHERE username = :username and isbn = :isbn", {"username": session["username"], "isbn": isbn}).fetchall()
    rev_done = len(user_reviews)
    return render_template("book.html", book = book, book_info = result, reviews = reviews, results = results, rev_done = rev_done, user_reviews = user_reviews)

@app.route("/register", methods=["GET", "POST"])
def register():
    """User Registration"""

    # Get form information.
    if request.method == "POST":

        if not request.form.get("username"):
            flash("Must provide username.")
            return redirect("/register")

        if not request.form.get("password"):
            flash("Must provide password.")
            return redirect("/register")

        if not request.form.get("email"):
            flash("Must provide email")
            return redirect("/register")

        if not request.form.get("name"):
            flash("Must provide name")
            return redirect("/register")

        username = request.form.get("username")
        hashed = generate_password_hash(request.form.get("password"))
        email = request.form.get("email")
        name = request.form.get("name")
        if request.form.get("password") != request.form.get("confirm_p"):
            flash("Password don't match")
            return redirect("/register")

        # Insert to DB
        db.execute("INSERT INTO users (username, password, email, name) VALUES (:username, :password, :email, :name)",
                {"username": username,"password": hashed, "email": email, "name": name})
        db.commit()
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/review/<isbn>", methods=["GET", "POST"])
def review(isbn):
    """Submit Book # REVIEW"""

    # Get form information.
    if request.method == "POST":
        review_text = request.form.get("review_text")
        rating = int(request.form.get("rating"))
        # Insert to DB
        username = session["username"]
        db.execute("INSERT INTO reviews (review_text, rating, username, isbn) VALUES (:review_text, :rating, :username, :isbn)",
                {"username": username,"review_text": review_text, "rating": rating, "isbn": isbn})
        db.commit()
        return redirect("/book_details/"+isbn)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to index
    return redirect("/")


@app.route("/api/<isbn>", methods=["GET"])
def api(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": f"%{isbn}%"}).fetchone()
    reviews = db.execute("SELECT COUNT(*) as num_reviews, AVG(rating) as avg_rating FROM reviews WHERE isbn LIKE :isbn", {"isbn": f"%{isbn}%"}).fetchone()
    if reviews["avg_rating"] is None:
        rating_avg = 0
    else:
        rating_avg = str(round(reviews["avg_rating"],1))

    book_json = {
            "title": book["title"],
            "author": book["author"],
            "year": book["year"],
            "isbn":book["isbn"],
            "review_count": reviews["num_reviews"],
            "average_score": rating_avg
            }
    res = make_response(jsonify(book_json), 200)
    return res

@app.route("/user_reviews", methods=["GET"])
def user_reviews():
    user_reviews = db.execute("SELECT * from reviews r JOIN books b ON r.isbn = b.isbn WHERE username = :username ORDER by r.date DESC",
                    {"username": session["username"]}).fetchall()
    count = len(user_reviews)
    return render_template("user_reviews.html", user_reviews = user_reviews,count = count)
