from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secretkey"


# ---------------- DATABASE INIT ----------------

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT,
            role TEXT,
            rating_avg REAL DEFAULT 0,
            total_ratings INTEGER DEFAULT 0,
            reliability_score INTEGER DEFAULT 100
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            employer_id INTEGER,
            worker_id INTEGER,
            status TEXT DEFAULT 'Open',
            payment_sent INTEGER DEFAULT 0,
            payment_received INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            worker_id INTEGER
        )
    ''')

    # Ratings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            rater_id INTEGER,
            rated_id INTEGER,
            rating INTEGER
        )
    ''')


    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("home.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  (name, email, password, role))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[4]
            return redirect("/dashboard")
        else:
            return "Invalid credentials"

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        SELECT rating_avg, reliability_score
        FROM users
        WHERE id=?
    """, (session["user_id"],))

    user_data = c.fetchone()
    conn.close()

    return render_template("dashboard.html",
                           role=session["role"],
                           user_data=user_data)


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/post_job", methods=["GET", "POST"])
def post_job():
    if "user_id" not in session or session["role"] != "employer":
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        employer_id = session["user_id"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO jobs (title, description, employer_id) VALUES (?, ?, ?)",
                  (title, description, employer_id))
        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("post_job.html")

@app.route("/jobs")
def view_jobs():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE status='Open'")
    jobs = c.fetchall()
    conn.close()

    return render_template("jobs.html", jobs=jobs)


@app.route("/apply/<int:job_id>")
def apply(job_id):
    if "user_id" not in session or session["role"] != "worker":
        return redirect("/login")

    worker_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO applications (job_id, worker_id) VALUES (?, ?)",
              (job_id, worker_id))
    conn.commit()
    conn.close()

    return redirect("/jobs")

@app.route("/applicants/<int:job_id>")
def view_applicants(job_id):
    if "user_id" not in session or session["role"] != "employer":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        SELECT users.id, users.name, users.email
        FROM applications
        JOIN users ON applications.worker_id = users.id
        WHERE applications.job_id = ?
    """, (job_id,))

    applicants = c.fetchall()
    conn.close()

    return render_template("applicants.html",
                       applicants=applicants,
                       job_id=job_id)


@app.route("/my_jobs")
def my_jobs():
    if "user_id" not in session or session["role"] != "employer":
        return redirect("/login")

    employer_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE employer_id=?", (employer_id,))
    jobs = c.fetchall()
    conn.close()

    return render_template("my_jobs.html", jobs=jobs)

@app.route("/select_worker/<int:job_id>/<int:worker_id>")
def select_worker(job_id, worker_id):
    if "user_id" not in session or session["role"] != "employer":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        UPDATE jobs 
        SET worker_id=?, status='In Progress'
        WHERE id=?
    """, (worker_id, job_id))

    conn.commit()
    conn.close()

    return redirect("/my_jobs")
@app.route("/payment_sent/<int:job_id>")
def payment_sent(job_id):
    if "user_id" not in session or session["role"] != "employer":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE jobs SET payment_sent=1 WHERE id=?", (job_id,))
    conn.commit()
    conn.close()

    return redirect("/my_jobs")

@app.route("/payment_received/<int:job_id>")
def payment_received(job_id):
    if "user_id" not in session or session["role"] != "worker":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        UPDATE jobs 
        SET payment_received=1, status='Completed'
        WHERE id=?
    """ , (job_id,))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/my_work")
def my_work():
    if "user_id" not in session or session["role"] != "worker":
        return redirect("/login")

    worker_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE worker_id=?", (worker_id,))
    jobs = c.fetchall()
    conn.close()

    return render_template("my_work.html", jobs=jobs)

@app.route("/rate/<int:job_id>/<int:rated_id>", methods=["GET", "POST"])
def rate(job_id, rated_id):
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        rating_value = int(request.form["rating"])
        rater_id = session["user_id"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        # Insert rating
        c.execute("""
            INSERT INTO ratings (job_id, rater_id, rated_id, rating)
            VALUES (?, ?, ?, ?)
        """, (job_id, rater_id, rated_id, rating_value))

        # Update average rating
        c.execute("""
            SELECT AVG(rating), COUNT(rating)
            FROM ratings
            WHERE rated_id=?
        """, (rated_id,))

        avg, count = c.fetchone()

        c.execute("""
            UPDATE users
            SET rating_avg=?, total_ratings=?
            WHERE id=?
        """, (avg, count, rated_id))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("rate.html", job_id=job_id, rated_id=rated_id)


@app.route("/delete_job/<int:job_id>")
def delete_job(job_id):
    if "user_id" not in session or session["role"] != "employer":
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Check if job has a worker assigned
    c.execute("""
        SELECT worker_id 
        FROM jobs 
        WHERE id=? AND employer_id=?
    """, (job_id, session["user_id"]))

    job = c.fetchone()

    if job:
        worker_id = job[0]

        # If worker was assigned, reduce reliability score
        if worker_id:
            c.execute("""
                UPDATE users
                SET reliability_score = reliability_score - 10
                WHERE id=?
            """, (session["user_id"],))

        # Delete the job
        c.execute("""
            DELETE FROM jobs
            WHERE id=? AND employer_id=?
        """, (job_id, session["user_id"]))

        conn.commit()

    conn.close()

    return redirect("/my_jobs")





# ---------------- MAIN ----------------
import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


