import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, lookup

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///programs.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Create this 1-element list to store the program id later in "def program()" idea inspired by github
x = []
x.append(0)

@app.route("/", methods=["GET", "POST"])
def homepage():
    #brings you to homepage
    if request.method == "POST":
        if not request.form.get("keyword"):
            return render_template("homepage.html")
        else:
            results = db.execute("SELECT * FROM programlist WHERE title LIKE :key", key="%" + request.form.get("keyword") + "%")
            return render_template("results.html", results=results)
    #first entrance to site
    else:
        return render_template("homepage.html")


@app.route("/results", methods=["GET", "POST"])
def results():
    #outputs search results when user searches up a program
    if request.method == "GET":
        if not request.form.get("title"):
            return render_template("results.html")
    else:
        info = db.execute("SELECT * FROM programlist WHERE title = name",
                                 name=request.form.get("title"))
        return render_template("program.html", info=info)


@app.route("/registerprogram", methods=["GET", "POST"])

def registerProgram():
    #Lets user register a new program for others to sponsor
    if request.method == "POST":
        y = request.form.get("title")
        quote = db.execute("SELECT 1 FROM programlist WHERE title = :x",x=y)

        if quote != []:
            flash("Program name already taken!")
            return render_template("registerprogram.html")
        db.execute("INSERT INTO programlist (title, org, type, description, money) VALUES (:til, :org, :typ, :des, :mon)",
                   til=y, org=request.form["org"], typ=request.form["type"], des=request.form["description"], mon = 0)
        #new page with registered program
        pid = db.execute("SELECT * FROM programlist WHERE title = :til", til=request.form["title"])
        pid = pid[0]
        pid = str(pid.get("id"))

        key = "/program?id=" + pid
        return redirect(key)
    else:
        return render_template("registerprogram.html")



@app.route("/program", methods=["GET", "POST"])
def program():
    #displays program information, /program doesnt exist but you have to put id after it

    if request.method == "POST":
        if not request.form["nickname"] or not request.form["rating"] or not request.form["review"]:
            return apology("must provide information", 403)
        # add user review
        db.execute("INSERT INTO reviews (programid, nickname, rating, title, review) VALUES (:name, :nickname, :rate, :title, :review)",
                   name=x[0], nickname=request.form["nickname"], rate=int(request.form["rating"]), title=request.form["title"], review=request.form["review"])
        programrating = db.execute("SELECT AVG(rating) FROM reviews WHERE programid = :name", name=x[0])
        programrating = programrating[0]
        programrating = int(programrating.get("AVG(rating)"))
        db.execute("UPDATE programlist SET rating = :rating WHERE id = :name", rating=programrating, name=x[0])
        key = "/program?id=" + x[0]
        return redirect(key)

    else:
        pid = request.args.get("id")
        x[0] = pid
        # Display program info and past user reviews
        programinfo = db.execute("SELECT * FROM programlist WHERE id = :pid", pid=pid)
        userreviews = db.execute("SELECT * FROM reviews WHERE programid = :pid", pid=pid)
        return render_template("program.html", info=programinfo[0], reviews=userreviews)




@app.route("/sponsor", methods=["GET", "POST"])

def sponsor():
    """sponsor a science program for children or smth"""
    if request.method == "POST":
        y = request.form.get("title")
        quote = db.execute("SELECT 1 FROM programlist WHERE title = :x",x=y)

        if quote == []:
            return apology("invalid title", 403)

        try:
            money = int(request.form.get("donation"))
        except:
            return apology("must be a positive integer", 403)

        if money <= 0:
            return apology("must be a positive integer", 403)

        # Query database for username
        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # How much $$$ the user still has in her account
        cash_remaining = rows[0]["cash"]


        if money > cash_remaining:
            return apology("not enough money to sponsor", 403)

        # Book keeping (TODO: should be wrapped with a transaction)
        db.execute("UPDATE users SET cash = cash - :price WHERE id = :user_id", price=money, user_id=session["user_id"])
        db.execute("INSERT INTO transactions (user_id, title, money) VALUES(:user_id, :title, :money)",
                   user_id=session["user_id"],
                   title=request.form.get("title"),
                   money = money)
        db.execute("UPDATE programlist SET money = money + :price WHERE title = :title", price=money, title=y)

        flash("Sponsored!")

        return redirect("/")

    else:
        return render_template("sponsor.html")



@app.route("/history")

def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT title, money, created_at FROM transactions WHERE user_id = :user_id ORDER BY created_at ASC", user_id=session["user_id"])
    userinfo = db.execute("SELECT cash FROM users WHERE id = :id", id =session["user_id"])


    return render_template("history.html", transactions=transactions, userinfo=userinfo)




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 403)


        hash = generate_password_hash(request.form.get("password"))
        new_user_id = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                                 username=request.form.get("username"),
                                 hash=hash)

        if not new_user_id:
            return apology("username taken", 403)


        # Remember which user has logged in
        session["user_id"] = new_user_id

        #flash
        flash("Registered! You have 10,000 dollars to start off with!")
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/funds/add", methods=["GET", "POST"])
def add_funds():

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount"))
        except:
            return apology("amount must be a positive real number", 403)

        db.execute("UPDATE users SET cash = cash + :amount WHERE id = :user_id", user_id=session["user_id"], amount=amount)

        flash("Funds have been updated!")

        return redirect("/")
    else:
        return render_template("add_funds.html")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

