import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///yourharvard.db")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show home page"""

    if request.method == "GET":

        # Get username to be displayed
        name = db.execute("SELECT name FROM users WHERE id =:user_id", user_id=session.get("user_id"))[0]['name']
        firstname = name.split()[0]
        # Getting list of all times in database
        times_raw = db.execute("SELECT daytime FROM courses GROUP BY daytime")
        # Allocating data set and iterating through elements to account for repeats
        times_set = set()
        for each in times_raw:
            for key in each:
                times_set.add(each[key])
        times = sorted(times_set)
        times_len = len(times)
        return render_template("index.html", times=times, times_len=times_len, firstname=firstname)

    else:
        "Search for course with specified title"

        # Find the course
        department = request.form.get("department")
        daytime = request.form.get("daytime")
        overall = request.form.get("overall")
        instrat = request.form.get("instrat")
        workload = request.form.get("workload")

        if not department == "Any Department":
            dept_courses = db.execute("SELECT id FROM courses WHERE department =:department", department=department)
        else:
            dept_courses = db.execute("SELECT id FROM courses")

        if not daytime == "Any Time":
            time_courses = db.execute("SELECT id FROM courses WHERE daytime =:daytime", daytime=daytime)
        else:
            time_courses = db.execute("SELECT id FROM courses")

        # Finds courses that meet the overall workload specification
        if overall == "Any Course Rating":
            overall_courses = db.execute("SELECT id FROM courses")
        elif overall == "3.0+":
            overall_courses = db.execute("SELECT id FROM courses WHERE overall >= '3'")
        elif overall == "3.5+":
            overall_courses = db.execute("SELECT id FROM courses WHERE overall >= '3.5'")
        elif overall == "4.0+":
            overall_courses = db.execute("SELECT id FROM courses WHERE overall >= '4'")
        elif overall == "4.5+":
            overall_courses = db.execute("SELECT id FROM courses WHERE overall >= '4.5'")
        elif overall == "5":
            overall_courses = db.execute("SELECT id FROM courses WHERE overall == '5'")

        # Finds courses that meet the instructor rating specification
        if instrat == "Any Instructor Rating":
            instrat_courses = db.execute("SELECT id FROM courses")
        elif instrat == "3.0+":
            instrat_courses = db.execute("SELECT id FROM courses WHERE instrat >= '3'")
        elif instrat == "3.5+":
            instrat_courses = db.execute("SELECT id FROM courses WHERE instrat >= '3.5'")
        elif instrat == "4.0+":
            instrat_courses = db.execute("SELECT id FROM courses WHERE instrat >= '4'")
        elif instrat == "4.5+":
            instrat_courses = db.execute("SELECT id FROM courses WHERE instrat >= '4.5'")
        elif instrat == "5":
            instrat_courses = db.execute("SELECT id FROM courses WHERE instrat == '5'")

        # Finds courses that meet the weekly workload specification
        if workload == "Any Weekly Workload":
            workload_courses = db.execute("SELECT id FROM courses")
        elif workload == "< 2 hrs":
            workload_courses = db.execute("SELECT id FROM courses WHERE work < '2'")
        elif workload == "2-4.9 hrs":
            workload_courses = db.execute("SELECT id FROM courses WHERE work >= '2' AND work < '5'")
        elif workload == "5-7.9 hrs":
            workload_courses = db.execute("SELECT id FROM courses WHERE work >= '5' AND work < '8'")
        elif workload == "8-10 hrs":
            workload_courses = db.execute("SELECT id FROM courses WHERE work >= '8' AND work <= '10'")
        elif workload == "> 10 hrs":
            workload_courses = db.execute("SELECT id FROM courses WHERE work > '10'")

        # Compile the selection of courses that match all specifications
        d = []
        t = []
        o = []
        i = []
        w = []
        for each in dept_courses:
            d.append(each['id'])
        for each in time_courses:
            t.append(each['id'])
        for each in overall_courses:
            o.append(each['id'])
        for each in instrat_courses:
            i.append(each['id'])
        for each in workload_courses:
            w.append(each['id'])

        similarities = set(d) & set(t) & set(o) & set(i) & set(w)

        result = []
        for each in similarities:
            result.append(db.execute(
                "SELECT id, title, instructor, daytime, overall, instrat, work, term FROM courses WHERE id=:each", each=each))
        total = len(result)

        return render_template("search.html", result=result, total=total, department=department, daytime=daytime, overall=overall, instrat=instrat, workload=workload)


@app.route("/quicksearch", methods=["POST"])
@login_required
def quicksearch():
    "Search quickly for courses using keyword(s)"
    # Get search input from the user
    course = request.form.get("course")
    # Get courses whose titles at all match what the user has searched
    result = db.execute(
        "SELECT id, title, instructor, daytime, overall, instrat, work, term FROM courses WHERE title LIKE :course", course="%" + course + "%")
    if not result:
        return apology("No courses found!", 403)

    # Get information for Jinja - such as total number of courses to display on the list
    total = len(result)

    # Get information for Jinja - such as times of courses for Advanced Search by Time dropdown (with no repeats)
    times_raw = db.execute("SELECT daytime FROM courses GROUP BY daytime")
    times_set = set()
    for each in times_raw:
        for key in each:
            times_set.add(each[key])
    times = sorted(times_set)
    times_len = len(times)
    return render_template("quicksearch.html", result=result, total=total, times=times, times_len=times_len, course=course)


@app.route("/course", methods=["GET"])
@login_required
def course():
    "Display individual course page"
    course = request.args.get("q")

    name = db.execute("SELECT name FROM users WHERE id =:user_id", user_id=session.get("user_id"))[0]['name']
    interest_now = db.execute("SELECT interest FROM courses WHERE id =:course", course=course)[0]['interest']
    names = interest_now.split(", ")
    to_add = True
    for each in names:
        if each == name:
            to_add = False
    if to_add == True:
        add_button = "I'm Interested!"
    else:
        add_button = "Remove Interest"

    comments_now = db.execute("SELECT comment FROM courses WHERE id =:course", course=course)[0]['comment']
    comments = comments_now.split("|@~")
    comlen = len(comments)

    result = db.execute(
        "SELECT id, title, instructor, daytime, description, department, gen, div, overall, instrat, work, interest, comment, term FROM courses WHERE id =:course", course=course)
    return render_template("course.html", result=result, add_button=add_button, comments=comments, comlen=comlen)


@app.route("/courses", methods=["GET"])
@login_required
def courses():
    result = db.execute("SELECT id, title, instructor, daytime, overall, instrat, work, term FROM courses WHERE common=1")
    total = len(result)

    times_raw = db.execute("SELECT daytime FROM courses GROUP BY daytime")
    times_set = set()
    for each in times_raw:
        for key in each:
            times_set.add(each[key])
    times = sorted(times_set)
    times_len = len(times)

    return render_template("courses.html", result=result, total=total, times=times, times_len=times_len)


@app.route("/interest", methods=["GET"])
@login_required
def interest():
    "Add/remove current user to list of interested students"
    # Get user's name
    name = db.execute("SELECT name FROM users WHERE id =:user_id", user_id=session.get("user_id"))[0]['name']
    # Get current course's name
    course = request.args.get("q")
    # Decide whether to add or remove the user from interested students
    interest_now = db.execute("SELECT interest FROM courses WHERE id =:course", course=course)[0]['interest']
    add_user = True
    names = interest_now.split(", ")
    if not interest_now == "No students":
        for each in names:
            if each == name:
                add_user = False

    if add_user == True:
        # Add name to current interest
        if interest_now == "No students":
            db.execute("UPDATE courses SET interest =:name WHERE id =:course", course=course, name=name)
            new_interest = db.execute("SELECT interest FROM courses WHERE id =:course", course=course)[0]['interest']
        else:
            add = True
            for each in names:
                if each == name:
                    return apology("You're already interested!", 403)
                    add = False
            if add == True:
                new_interest = interest_now + ", " + name
                db.execute("UPDATE courses SET interest =:new_interest WHERE id =:course", course=course, new_interest=new_interest)

    else:
        # Remove user from current interest
        for each in names:
            if each == name:
                names.remove(each)
        # Rebuild list of names
        new_interest = ""
        if len(names) == 0:
            new_interest = "No students"
        else:
            i = 0
            for each in names:
                if i == 0:
                    new_interest = each
                else:
                    new_interest = new_interest + ", " + each
                    i += 1
        db.execute("UPDATE courses SET interest =:new_interest WHERE id =:course", course=course, new_interest=new_interest)

    course_url = "/course?q=" + course
    return redirect(course_url)


@app.route("/comment", methods=["POST"])
@login_required
def comment():
    "Add comment to the list of comments"
    # Get user's name
    name = db.execute("SELECT name FROM users WHERE id =:user_id", user_id=session.get("user_id"))[0]['name']
    # Get current course's name
    course = request.args.get("q")
    # Get comment to be inserted
    comment = request.form.get("comment")
    # Decide whether to add or remove the user from interested students
    comments_now = db.execute("SELECT comment FROM courses WHERE id =:course", course=course)[0]['comment']
    comments = comments_now.split("|@~")
    if not comments[0] == "No comments":
        comments.append(comment)
        new_comments = comments[0]
        for each in comments:
            if not each == comments[0]:
                new_comments = new_comments + "|@~" + each
        db.execute("UPDATE courses SET comment =:new_comments WHERE id =:course", course=course, new_comments=new_comments)
    else:
        new_comments = comment
        db.execute("UPDATE courses SET comment =:new_comments WHERE id =:course", course=course, new_comments=new_comments)

    course_url = "/course?q=" + course
    return redirect(course_url)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "GET":
        "Display current user's profile page"
        result = db.execute("SELECT username, name, house, year, concentration, bio FROM users WHERE id=:user_id",
                            user_id=session.get("user_id"))
        return render_template("profile.html", result=result)
    else:
        username = db.execute("SELECT username FROM users WHERE id =:user_id", user_id=session.get("user_id"))[0]['username']
        bioupdate = request.form.get("bioupdate")
        db.execute("UPDATE users SET bio=:bioupdate WHERE username=:username", bioupdate=bioupdate, username=username)
        return redirect("/profile")


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
    """Register user"""

    if request.method == "POST":

        # Get user input
        if not request.form.get("username"):
            return apology("Missing Username!")
        if not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Missing Password!")
        if not (request.form.get("password") == request.form.get("confirmation")):
            return apology("Passwords do not match!")
        if not request.form.get("name"):
            return apology("Missing name!")
        if not request.form.get("house"):
            return apology("Missing House/Dorm!")
        if not request.form.get("concentration"):
            return apology("Missing concentration! If you have yet to declare, select 'Undeclared'")
        if not request.form.get("year"):
            return apology("Missing class year!")

        # Hash users password, proceed to store data for new user
        hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        result = db.execute("INSERT INTO users (username, hash, name, house, concentration, year) VALUES(:username, :hash, :name, :house, :concentration, :year)",
                            username=request.form.get("username"), hash=hash, name=request.form.get("name"), house=request.form.get("house"), concentration=request.form.get("concentration"), year=request.form.get("year"))
        if not result:
            return apology("Registration failed")

        # Log the new user in
        username = request.form.get("username")
        user_id = db.execute("SELECT id FROM users WHERE username =:username", username=username)
        session["user_id"] = result

        return redirect("/")

    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
