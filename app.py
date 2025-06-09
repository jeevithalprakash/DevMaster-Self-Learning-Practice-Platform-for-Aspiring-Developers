from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # for session security

# Create DB if it doesn't exist
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    if 'username' in session:
        return f"Welcome {session['username']}! <br><a href='/logout'>Logout</a>"
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                      (username, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists. <a href='/signup'>Try again</a>"
        conn.close()
        return redirect('/login')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[0], password):
            session['username'] = username
            return redirect('/dashboard')
        else:
            return "Invalid credentials. <a href='/login'>Try again</a>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        new_password = request.form['new_password']
        
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND email=?", (username, email))
        user = c.fetchone()
        
        if user:
            c.execute("UPDATE users SET password=? WHERE username=? AND email=?", 
                      (new_password, username, email))
            conn.commit()
            conn.close()
            return "Password reset successful! <a href='/login'>Login now</a>"
        else:
            conn.close()
            return "Invalid username/email. <a href='/forgot-password'>Try again</a>"
        
    return render_template('forgot_password.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        c.execute("INSERT INTO goals (username, title, description) VALUES (?, ?, ?)",
                  (username, title, description))
        conn.commit()

    c.execute("SELECT * FROM goals WHERE username=?", (username,))
    goals = c.fetchall()
    conn.close()

    return render_template('dashboard.html', goals=goals, username=username)

@app.route('/update-goal/<int:goal_id>')
def update_goal(goal_id):
    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()

    # Fetch current status
    c.execute("SELECT status FROM goals WHERE id=?", (goal_id,))
    status = c.fetchone()[0]

    # Cycle through status
    next_status = 'In Progress' if status == 'Pending' else 'Completed' if status == 'In Progress' else 'Pending'

    c.execute("UPDATE goals SET status=? WHERE id=?", (next_status, goal_id))
    conn.commit()
    conn.close()

    return redirect('/dashboard')

@app.route('/delete-goal/<int:goal_id>')
def delete_goal(goal_id):
    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute("DELETE FROM goals WHERE id=?", (goal_id,))
    conn.commit()
    conn.close()

    return redirect('/dashboard')

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect('/login')

    username = session['username']

    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()

    # Get all goals for the logged-in user
    c.execute("SELECT title, description, status FROM goals WHERE username=?", (username,))
    rows = c.fetchall()

    goals = []
    completed_count = 0

    for row in rows:
        goals.append({
            'title': row[0],
            'description': row[1],
            'status': row[2]
        })
        if row[2].lower() == 'completed':
            completed_count += 1

    total_goals = len(goals)

    conn.close()

    return render_template('profile.html', username=username, goals=goals, completed=completed_count, total=total_goals)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)