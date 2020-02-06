from flask import Flask, redirect, render_template, session, url_for, request, flash, abort, jsonify, make_response
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker, scoped_session
from flask_session import Session
from werkzeug import secure_filename
import re
import datetime
import os
import functools


app = Flask(__name__)
application = app


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = "efd432e0aca715610c505c533037b95d6fb22f5692a0d33820ab7b19ef06f513"
app.config['UPLOAD_FOLDER'] = 'static/images/uploads'

app.config['ALLOWED_EXT'] = ['jpg', 'jpeg', 'png', 'gif', ]

db_string = 'postgres+psycopg2://geojoe_geoffery:donsniper123@localhost:5432/geojoe_flask'
engine = create_engine(db_string)
db = scoped_session(sessionmaker(bind=engine))

# = scoped_session(sessionmaker(bind=engine))

# user table
db.execute('''CREATE TABLE IF NOT EXISTS users(
                user_id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL,
                username VARCHAR NOT NULL,
                email VARCHAR NOT NULL,
                password VARCHAR,
                UNIQUE(username, email))''')


# posts table
db.execute('''CREATE TABLE IF NOT EXISTS posts(
                post_id SERIAL PRIMARY KEY,
                title VARCHAR NOT NULL,
                slug VARCHAR UNIQUE,
                body TEXT NOT NULL,
                date_published TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                author INTEGER,
                FOREIGN KEY(author) REFERENCES users(user_id))''')
db.commit()


def login_required(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return func(*args, **kwargs)
    return wrapper


# Home page
@app.route('/')
def index():

    posts = db.execute(
        "select title, slug, body, name, date_published  from posts, users where users.user_id=posts.author order by date_published desc")
    return render_template('index.html', posts=posts)


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        next_url = request.form["next"]

        user = db.execute(
            "select * from users where username= :username", {"username": username}).fetchone()

        if user:
            session['username'] = user.username
            session['name'] = user.name
            session['email'] = user.email

            if next_url:
                return redirect(next_url)

            flash('Log in Successful')
            return redirect(url_for('index'))
        else:
            flash('Username or Password incorrect')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    session.pop('name', None)
    session.pop('email', None)
    return redirect(url_for('index'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        try:
            db.execute("insert into users(name, username, email, password) values(:name, :username, :email, :password)", {
                       "name": name, "username": username, "email": email, "password": password})
            db.commit()
            return redirect(url_for('login'))
        except exc.IntegrityError:
            flash('Username Already exists, please try another')
            return redirect(url_for('signup'))
    return render_template('signup.html')


@app.route('/profile')
@login_required
def profile():
    username = session['username']
    name = session['name']
    email = session['email']

    posts = db.execute("select title, post_id, slug, body, date_published, name from posts, users where users.user_id=posts.author and users.username = :username order by date_published desc", {
        "username": username})
    return render_template('profile.html', username=username, name=name, email=email, posts=posts)


@app.route('/edit_post', methods=['POST', 'GET'])
@login_required
def edit_post():
    if request.method == 'POST':
        username = session['username']
        post_title = request.form['post_title']
        post_body = request.form['post_body']
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', post_title.lower())
        author = db.execute("select user_id from users where username = :username", {
                            "username": username}).fetchone()[0]

        db.execute("insert into posts(title, slug, body, author) values(:post_title, :slug, :post_body, :author)",
                   {"post_title": post_title, "slug": slug, "post_body": post_body, "author": author})
        db.commit()

        return redirect(url_for('profile'))
    post = {}
    return render_template('edit_post.html', post=post)


@app.route('/delete/<int:id>')
@login_required
def delete_post(id):
    db.execute("delete from posts where post_id = :id", {'id': id})
    db.commit()
    return redirect(url_for('profile'))


@app.route('/update/<int:id>', methods = ['GET', 'POST'])
@login_required
def update_post(id):
    if request.method == 'POST':
        title = request.form['post_title']
        body = request.form['post_body']
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower())


        db.execute("update posts set title = :title, body = :body, slug = :slug where post_id = :id", {
                   'title': title, 'body': body, 'slug': slug, 'id': id})
        db.commit()

        return redirect(url_for('profile'))
    
    post = db.execute("select title, body from posts where post_id = :id", {'id': id}).fetchone()
    return render_template('edit_post.html', post = post)    


@app.route('/<slug>')
def post(slug):

    picture = ""
    posts = db.execute("select title, date_published, body, name from posts, users where users.user_id = posts.author and posts.slug = :slug", {
                       "slug": slug}).fetchone()
    return render_template('post.html', post=posts, picture=picture)


def allowed_file(filename):
    allowed_ext = app.config['ALLOWED_EXT']
    exp = '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext
    return exp


@app.route("/upload/", methods=['POST'])
def upload():
    if request.method == 'POST':
        if request.files:
            image = request.files['image']

            if image.filename == '':
                responce_msg = {"success": False,
                                "msg": "no file name", "status": 404}
                res = make_response(jsonify(responce_msg))
                return res

            if allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(
                    app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                responce_msg = {"data": {"link": image_path},
                                "success": True, "status": 200}
                res = make_response(jsonify(responce_msg))
                return res
            else:
                responce_msg = {"success": False,
                                "msg": "invalid file type", "status": 404}
                res = make_response(jsonify(responce_msg))
                return res

    return redirect(request.url)


@app.shell_context_processor
def make_shell_context():
    return {'db': db}


if __name__ == "__main__":
    app.run(debug=True)
