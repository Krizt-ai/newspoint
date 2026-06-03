import os
import requests

# ================= DATABASE =================
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3306))


mysql = MySQL(app)
bcrypt = Bcrypt(app)

# ================= API =================

API_KEY = "bf0b5c8daef6217083fa638d9f9d2762"

# ================= GLOBAL BOOKMARK COUNT =================

@app.context_processor
def inject_bookmarks():

    total_bookmarks = 0

    if 'user' in session:

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT id FROM users WHERE username=%s",
            (session['user'],)
        )

        user = cur.fetchone()

        if user:

            user_id = user[0]

            cur.execute(
                "SELECT COUNT(*) FROM bookmarks WHERE user_id=%s",
                (user_id,)
            )

            total_bookmarks = cur.fetchone()[0]

        cur.close()

    return dict(total_bookmarks=total_bookmarks)

# ================= GET NEWS =================

def get_news(query):

    url = f"https://gnews.io/api/v4/search?q={query}&lang=en&max=20&token={API_KEY}"

    try:

        response = requests.get(url)

        data = response.json()

        return data.get("articles", [])

    except:

        return []

# ================= HOME =================

@app.route('/')
def home():
    return "Homepage is working!"
    ph_news = get_news("philippines")

    intl_news = get_news("world")

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM news ORDER BY id DESC"
    )

    local_news = cur.fetchall()

    cur.close()

    return render_template(
        'home.html',
        ph_news=ph_news,
        intl_news=intl_news,
        local_news=local_news
    )

# ================= CATEGORY =================

@app.route('/category/<name>')
def category(name):

    articles = get_news(name)

    return render_template(
        'category.html',
        articles=articles,
        title=name.capitalize()
    )

# ================= LOGIN + REGISTER =================

@app.route('/auth', methods=['GET', 'POST'])
def auth():

    if request.method == 'POST':

        action = request.form.get('action')

        username = request.form['username'].strip()
        password = request.form['password']

        cur = mysql.connection.cursor()

        # ================= REGISTER =================

        # ================= REGISTER =================

        if action == 'register':

            # CLEAN INPUTS
            username = username.strip()

            # VALIDATION
            if len(username) < 4:
                cur.close()

                return render_template(
                    'auth.html',
                    error="Username must contain at least 4 characters."
                )

            if len(password) < 6:
                cur.close()

                return render_template(
                    'auth.html',
                    error="Password must contain at least 6 characters."
                )

            # CHECK EXISTING USER
            cur.execute(
                "SELECT id FROM users WHERE username=%s",
                (username,)
            )

            existing = cur.fetchone()

            if existing:
                cur.close()

                return render_template(
                    'auth.html',
                    error="This username is already registered. Please choose another username."
                )

            try:

                # HASH PASSWORD
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

                # INSERT USER
                cur.execute(
                    """
                    INSERT INTO users(username,password,role)
                    VALUES(%s,%s,%s)
                    """,
                    (username, hashed_password, "user")
                )

                mysql.connection.commit()

                cur.close()

                # REDIRECT TO AUTH PAGE WITH SUCCESS MESSAGE
                return render_template(
                    'auth.html',
                    success="Registration completed successfully. Please login to continue."
                )

            except Exception:

                mysql.connection.rollback()

                cur.close()

                return render_template(
                    'auth.html',
                    error="Unable to create your account right now. Please try again later."
                )
        # ================= LOGIN =================

        if action == 'login':

            cur.execute(
                "SELECT * FROM users WHERE username=%s",
                (username,)
            )

            user = cur.fetchone()

            cur.close()

            if not user:

                return render_template(
                    'auth.html',
                    error="Invalid username or password."
                )

            try:

                if bcrypt.check_password_hash(user[2], password):

                    session['user'] = user[1]
                    session['role'] = user[3]

                    if user[3] == 'admin':

                        return redirect('/admin')

                    return redirect('/dashboard')

                else:

                    return render_template(
                        'auth.html',
                        error="Invalid username or password."
                    )

            except:

                return render_template(
                    'auth.html',
                    error="Authentication system error."
                )

    return render_template('auth.html')

# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

# ================= BOOKMARK =================

@app.route('/bookmark')
def bookmark():

    if 'user' not in session:

        return redirect('/auth')

    title = request.args.get('title')
    url = request.args.get('url')
    image = request.args.get('image')

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT id FROM users WHERE username=%s",
        (session['user'],)
    )

    user = cur.fetchone()

    if user:

        user_id = user[0]

        cur.execute(
            """
            SELECT * FROM bookmarks
            WHERE user_id=%s AND url=%s
            """,
            (user_id, url)
        )

        existing = cur.fetchone()

        if not existing:

            cur.execute(
                """
                INSERT INTO bookmarks(user_id,title,url,image)
                VALUES(%s,%s,%s,%s)
                """,
                (user_id, title, url, image)
            )

            mysql.connection.commit()

    cur.close()

    return redirect('/dashboard')

# ================= REMOVE BOOKMARK =================

@app.route('/remove_bookmark/<int:id>')
def remove_bookmark(id):

    if 'user' not in session:

        return redirect('/auth')

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM bookmarks WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()

    cur.close()

    return redirect('/dashboard')

# ================= DASHBOARD =================

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:

        return redirect('/auth')

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT id FROM users WHERE username=%s",
        (session['user'],)
    )

    user = cur.fetchone()

    bookmarks = []

    if user:

        user_id = user[0]

        cur.execute(
            """
            SELECT * FROM bookmarks
            WHERE user_id=%s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        bookmarks = cur.fetchall()

    cur.close()

    return render_template(
        'dashboard.html',
        bookmarks=bookmarks
    )

# ================= ADMIN =================

@app.route('/admin', methods=['GET', 'POST'])
def admin():

    if 'user' not in session:

        return redirect('/auth')

    if session.get('role') != 'admin':

        return redirect('/')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        title = request.form['title']
        content = request.form['content']
        category = request.form['category']

        cur.execute(
            """
            INSERT INTO news(title,content,category,image)
            VALUES(%s,%s,%s,%s)
            """,
            (title, content, category, "")
        )

        mysql.connection.commit()

    # POSTS

    cur.execute(
        "SELECT * FROM news ORDER BY id DESC"
    )

    posts = cur.fetchall()

    # USERS

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    total_admins = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE role='user'")
    total_normal_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM news")
    total_posts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookmarks")
    total_bookmarks = cur.fetchone()[0]

    cur.close()

    return render_template(
        'admin.html',
        posts=posts,
        total_users=total_users,
        total_admins=total_admins,
        total_normal_users=total_normal_users,
        total_posts=total_posts,
        total_bookmarks=total_bookmarks
    )

# ================= RUN =================

if __name__ == '__main__':

    app.run(debug=True)
