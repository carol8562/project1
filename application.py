import os
import requests

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

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

@app.route("/log_in_or_sign_up/<int:login>")
def log_in_or_sign_up(login):
    """ Presents a login page or a signup page """
    """ depending on whether or not 'login' is True """
    return render_template("log_in_or_sign_up.html", login=login)

@app.route("/login/<int:login>", methods=["POST"])
def login(login):
    """ Logs in (if 'login' is True) else signs up user """
    name=request.form.get("name")
    password=request.form.get("password")
    name_blank = (name == None or name == "")
    password_invalid = (password == None or len(password) < 8 or not (any(char.isdigit() for char in password)))
    # Check for blank fields or invalid passwords
    if name_blank or password_invalid:
        message = "Please enter "
        if name_blank:
            message += "your username"
            if password_invalid:
                message += " and "
        if password_invalid:
            message += "a valid password"
        message += "."
        return render_template("error.html", message=message, logging_in=True, login=login)
    # Look up user in database and react appropriately
    # depending on whether the user has chosen to log in or to sign up
    user = db.execute("SELECT * FROM users WHERE name=:name", {"name":name}).fetchone()
    if user == None:
        if login:
            return render_template("error.html", message="Please check your username", logging_in=True, login=login)
        else:
            db.execute("INSERT INTO users (name, password) VALUES (:name, :password)", {"name":name, "password":password})
            db.commit()
            checked_userid = db.execute("SELECT id FROM users WHERE name=:name AND password=:password", {"name":name, "password":password}).fetchone()
    else:
        if not login:
            return render_template("error.html", message="Please choose another username", logging_in=True, login=login)
        else:
            checked_userid = db.execute("SELECT id FROM users WHERE name=:name AND password=:password", {"name":name, "password":password}).fetchone()
            if checked_userid == None:
                return render_template("error.html", message="Please check your password", logging_in=True, login=login)
    if checked_userid == None:
        return render_template("error.html", message="Could not log you in. Please try again", logging_in=True, login=login)
    else:
        session['userid'] = checked_userid.id;
    return redirect(url_for('search', alert_info='0,""'))

@app.route("/logout")
def logout():
    """ Logs out user and returns to front page """
    session['userid'] = None;
    return render_template("index.html")

@app.route("/search/<string:alert_info>")
def search(alert_info):
    alert_list = alert_info.split(',')
    alert_should_be_visible = int(alert_list[0])
    alert_text = alert_list[1]
    print(f"alert_should_be_visible={alert_should_be_visible}, alert_text={alert_text}")
    return render_template("search.html", alert_should_be_visible=alert_should_be_visible, alert_text=alert_text)

@app.route("/search_results", methods=["GET", "POST"])
def search_results():
    if request.method == "POST":
        """ Lists all books satisfying search criteria on search.html """
        """ Presents an alert if no books found """
        isbn = request.form.get("isbn")
        author = request.form.get("author")
        title = request.form.get("title")
        isbn_isblank = isbn == None or isbn == ""
        author_isblank = author == None or author == ""
        title_isblank = title == None or title == ""
        if (isbn_isblank and author_isblank and title_isblank):
            return redirect(url_for('search', alert_info="1,Please enter at least one search criterion"))
        query = "SELECT * FROM books WHERE "
        if not isbn_isblank:
            isbn = f"%{ isbn }%"
            query += "isbn ILIKE :isbn"
            if not (author_isblank and title_isblank):
                query += " OR "
        if not author_isblank:
            author = f"%{ author }%"
            query += "author ILIKE :author"
            if not title_isblank:
                query += " OR "
        if not title_isblank:
            title = f"%{ title }%"
            query += "title ILIKE :title"
        query += " ORDER BY title"
        results = db.execute(query, {"isbn":isbn, "author":author, "title":title}).fetchall()
        session['results'] = results
    else:
        results = session['results']
    if results == None or len(results) == 0:
        message = '1,No books were found matching your search criteria'
        return redirect(url_for('search', alert_info=message))
    else:
        return render_template("search_results.html", results=results)

@app.route("/book/<string:isbn>", methods=["GET", "POST"])
def book(isbn):
    """ Lists details about the book with the given isbn """
    # Make sure book exists
    book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn":isbn}).fetchone()
    if book is None:
        return redirect(url_for('search', alert_info=f"1,No book exists with ISBN { isbn }"))
    if request.method == "POST":
        review = request.form.get("review")
        stars = request.form.get("stars")
        alreadyreviewed = db.execute("SELECT count( * ) FROM reviews WHERE isbn=:isbn AND userid=:userid", {"isbn":isbn, "userid":session["userid"]}).fetchone()[0]
        if alreadyreviewed:
            return redirect(url_for('search', alert_info=f"1,You have already reviewed { book[1] } by { book[2] }"))
        else:
            db.execute("INSERT INTO reviews (isbn, userid, review, stars) VALUES (:isbn, :userid, :review, :stars)", {"isbn":isbn, "userid":session["userid"], "review":review, "stars":stars})
            db.commit()
            return redirect(url_for('book', isbn=isbn))
    reviews = find_reviews(isbn)
    # Record reviewer's name to each review
    review_results = []
    user_has_reviewed_book = False
    for review in reviews:
        reviewer = db.execute("SELECT * FROM users WHERE id=:id", {"id":review.userid}).fetchone()
        review_results.append({"review":review, "reviewer":reviewer.name, "reviewer_is_user":(reviewer.id == session['userid'])})
        if reviewer.id == session['userid']:
            user_has_reviewed_book = True
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"6sl95IxA5KZkDqbRBkB9vQ", "isbns": isbn})
    if res.status_code != 404:
        average_rating = res.json()['books'][0]['average_rating']
        ratings_count = format(res.json()['books'][0]['ratings_count'], ',d')
        there_are_goodreads_ratings = True
    else:
        average_rating = None
        ratings_count = None
        there_are_goodreads_ratings = False
    return render_template("book.html", book=book, therearereviews=(len(reviews) > 0), review_results=review_results, user_has_not_reviewed_book=not user_has_reviewed_book, average_rating=average_rating, ratings_count=ratings_count, there_are_goodreads_ratings=there_are_goodreads_ratings)

def find_reviews(isbn):
    results = db.execute("SELECT review, userid, stars FROM reviews WHERE isbn=:isbn", {"isbn":isbn}).fetchall()
    return results

@app.route("/api/<string:isbn>")
def book_api(isbn):
    """Return details about a single book"""
    # Make sure book exists
    book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn":isbn}).fetchone()
    if book is None:
        return jsonify("error", f"No book exists in our database with ISBN { isbn }"), 404
    reviews = find_reviews(isbn)
    review_count = len(reviews)
    average_score = 0
    if review_count > 0:
        for review in reviews:
            average_score += review.stars
        average_score /= review_count
        average_score =  round(average_score, 1)
    # Get all passengers
    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.pub_year,
        "isbn": isbn,
        "review_count": review_count,
        "average_score": average_score
    })
