from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change_this_secret_for_production"  # change this


# --- MySQL / XAMPP config ---
def get_db():
    # Basic MySQL connection (no try/except)
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # XAMPP default: no password
        database="talenthub_db"
    )


# ---------------- Routes ----------------

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT jobs.id, jobs.title, jobs.description, jobs.category, jobs.budget,
               users.username AS client_name, jobs.created_at
        FROM jobs
        JOIN users ON users.id = jobs.client_id
        ORDER BY jobs.created_at DESC LIMIT 12
    """)
    jobs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", jobs=jobs)


# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if "logged_in" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "freelancer")

        if not username or not email or not password:
            flash("Please fill all fields")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
                       (username, email, hashed, role))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Registration successful. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if "logged_in" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # ✅ Save user info in session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["logged_in"] = True

            flash("Logged in successfully.")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials")
            return redirect(url_for("login"))

    return render_template("login.html")


# --- Forgot Password ---
@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            # For now, we’ll just show a success message.
            # (You can later add email reset functionality.)
            flash("Password reset instructions have been sent to your email.", "success")
            return redirect(url_for("login"))
        else:
            flash("No account found with that email address.", "danger")
            return redirect(url_for("forgot_password"))

    return render_template("forgot.html")



# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("index"))


# Dashboard (role-based)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = session["user_id"]
    role = session.get("role")
    username = session.get("username", "User")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if role == "client":
    # ----- CLIENT DASHBOARD -----
        cursor.execute("""
            SELECT j.*, 
                COUNT(a.id) AS total_applications,
                SUM(CASE WHEN a.status='Accepted' THEN 1 ELSE 0 END) AS accepted_count,
                SUM(CASE WHEN a.status='Rejected' THEN 1 ELSE 0 END) AS rejected_count,
                SUM(CASE WHEN a.status='Pending' THEN 1 ELSE 0 END) AS pending_count
            FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE j.client_id=%s
            GROUP BY j.id
            ORDER BY j.created_at DESC
        """, (uid,))
        jobs = cursor.fetchall()

        # Overall stats
        total_jobs = len(jobs)
        total_applications = sum(job["total_applications"] for job in jobs)
        accepted_jobs = sum(job["accepted_count"] for job in jobs)
        rejected_jobs = sum(job["rejected_count"] for job in jobs)
        pending_jobs = sum(job["pending_count"] for job in jobs)

        cursor.close()
        conn.close()

        return render_template(
            "dashboard_client.html",
            client_name=username,
            jobs=jobs,
            total_jobs=total_jobs,
            total_applications=total_applications,
            accepted_jobs=accepted_jobs,
            rejected_jobs=rejected_jobs,
            pending_jobs=pending_jobs
        )


    else:
        # ----- FREELANCER DASHBOARD -----
        cursor.execute("""
            SELECT a.*, j.title AS job_title, j.client_id
            FROM applications a
            JOIN jobs j ON j.id = a.job_id
            WHERE a.freelancer_id=%s
            ORDER BY a.created_at DESC
        """, (uid,))
        applied_jobs = cursor.fetchall()

        # ✅ Count applications by status
        total_applications = len(applied_jobs)
        accepted_count = sum(1 for a in applied_jobs if a["status"].lower() == "accepted")
        rejected_count = sum(1 for a in applied_jobs if a["status"].lower() == "rejected")
        pending_count = sum(1 for a in applied_jobs if a["status"].lower() == "pending")

        cursor.close()
        conn.close()

        return render_template(
            "dashboard_freelancer.html",
            freelancer_name=username,
            applied_jobs=applied_jobs,
            total_applications=total_applications,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            pending_count=pending_count
        )

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, email FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('profile.html', user=user)


@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        flash("You must be logged in.", "danger")
        return redirect(url_for('login'))

    old_password = request.form['old_password']
    new_password = request.form['new_password']

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch existing password hash
    cursor.execute("SELECT password FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    if not user or not check_password_hash(user['password'], old_password):
        flash("Incorrect old password.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('profile'))

    # Update new password
    new_hashed = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed, session['user_id']))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Password updated successfully!", "success")
    return redirect(url_for('profile'))


@app.route("/post_job", methods=["GET", "POST"])
def post_job():
    if "user_id" not in session or session.get("role") != "client":
        flash("Only clients can post jobs.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        budget = request.form.get("salary") or 0  # Fixed field name

        try:
            budget = float(budget)
        except ValueError:
            budget = 0.0

        if not title or not description:
            flash("Please provide title and description.")
            return redirect(url_for("post_job"))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (client_id, title, category, description, budget) VALUES (%s,%s,%s,%s,%s)",
            (session["user_id"], title, category, description, budget)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Job posted successfully.")
        return redirect(url_for("dashboard"))

    return render_template("post_job.html")

# Jobs listing (browse)
@app.route("/jobs")
def jobs():
    q = request.args.get("search", "").strip()
    cat = request.args.get("category", "").strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    base_sql = """
        SELECT jobs.id, jobs.title, jobs.description, jobs.category, jobs.budget,
               users.username AS username, jobs.created_at
        FROM jobs
        JOIN users ON users.id = jobs.client_id
    """
    where_clauses = []
    params = []

    if q:
        where_clauses.append("(jobs.title LIKE %s OR jobs.description LIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    if cat:
        where_clauses.append("jobs.category = %s")
        params.append(cat)

    if where_clauses:
        base_sql += " WHERE " + " AND ".join(where_clauses)

    base_sql += " ORDER BY jobs.created_at DESC"

    cursor.execute(base_sql, tuple(params))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("jobs.html", jobs=results)


# Job detail + show apply form
@app.route("/job/<int:job_id>", methods=["GET"])
def job_detail(job_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT j.*, u.username AS username
        FROM jobs j JOIN users u ON u.id = j.client_id
        WHERE j.id = %s
    """, (job_id,))
    job = cursor.fetchone()

    applicants = []
    if "user_id" in session and session.get("role") == "client" and job and job["client_id"] == session["user_id"]:
        cursor.execute("""
            SELECT a.*, u.username AS freelancer_name
            FROM applications a JOIN users u ON u.id = a.freelancer_id
            WHERE a.job_id = %s
            ORDER BY a.created_at DESC
        """, (job_id,))
        applicants = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("job_detail.html", job=job, applicants=applicants)


# Apply to a job (freelancer)
@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply(job_id):
    if "user_id" not in session or session.get("role") != "freelancer":
        flash("Only freelancers can apply.")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jobs WHERE id=%s", (job_id,))
    job = cursor.fetchone()

    if request.method == "POST":
        proposal = request.form.get("proposal", "").strip()
        if not proposal:
            flash("Please write a proposal.")
            cursor.close()
            conn.close()
            return redirect(url_for("apply", job_id=job_id))

        cursor2 = conn.cursor()
        cursor2.execute("INSERT INTO applications (job_id, freelancer_id, proposal) VALUES (%s,%s,%s)",
                        (job_id, session["user_id"], proposal))
        conn.commit()
        cursor2.close()
        flash("Application submitted.")
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))

    cursor.close()
    conn.close()
    return render_template("apply.html", job=job)


# Update application status (client)
@app.route("/application/<int:app_id>/update", methods=["POST"])
def update_application(app_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    new_status = request.form.get("status", "Pending")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT j.client_id FROM applications a JOIN jobs j ON a.job_id=j.id WHERE a.id=%s", (app_id,))
    row = cursor.fetchone()
    if not row:
        flash("Application not found.")
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))

    client_id = row[0]
    if client_id != session["user_id"]:
        flash("Unauthorized.")
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))

    cursor.execute("UPDATE applications SET status=%s WHERE id=%s", (new_status, app_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Application updated.")
    return redirect(url_for("dashboard"))



# Messaging (send + inbox)
@app.route("/messages", methods=["GET", "POST"])
def messages():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        receiver_id = request.form.get("receiver_id")
        message = request.form.get("message", "").strip()
        if receiver_id and message:
            cursor2 = conn.cursor()
            cursor2.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s,%s,%s)",
                            (uid, receiver_id, message))
            conn.commit()
            cursor2.close()
            flash("Message sent.")

    cursor.execute("""
        SELECT m.*, s.username AS sender_name
        FROM messages m JOIN users s ON s.id = m.sender_id
        WHERE m.receiver_id = %s
        ORDER BY m.timestamp DESC
    """, (uid,))
    inbox = cursor.fetchall()

    cursor.execute("SELECT id, username FROM users WHERE id != %s", (uid,))
    users = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("messages.html", inbox=inbox, users=users)


# Delete job (client only)
@app.route("/delete_job/<int:job_id>", methods=["GET"])
def delete_job(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT client_id FROM jobs WHERE id=%s", (job_id,))
    row = cursor.fetchone()
    if not row:
        flash("Job not found.")
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))
    if row[0] != session["user_id"]:
        flash("Unauthorized.")
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))

    cursor.execute("DELETE FROM jobs WHERE id=%s", (job_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Job deleted.")
    return redirect(url_for("dashboard"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    user_id = session.get("user_id")
    user_name = None
    user_email = None

    # 🧠 Fetch logged-in user info
    if user_id:
        cursor.execute("SELECT username, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            user_name = user["username"]
            user_email = user["email"]

    # 📨 Handle form submit
    if request.method == "POST":
        name = request.form.get("name") or user_name
        email = request.form.get("email") or user_email
        subject = request.form.get("subject")
        message = request.form.get("message")

        if subject and message:
            cursor.execute("""
                INSERT INTO contact_messages (user_id, name, email, subject, message, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (user_id, name, email, subject, message))
            conn.commit()
            flash("✅ Your message has been sent!", "success")
            return redirect(url_for("contact"))
        else:
            flash("⚠️ Please fill all fields.", "danger")

    cursor.close()
    conn.close()

    return render_template("contact.html", user_name=user_name, user_email=user_email)


# Run app
if __name__ == "__main__":
    app.run(debug=True)
