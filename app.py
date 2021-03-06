from flask import Flask, redirect, render_template, session, url_for, request, flash
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker, scoped_session
from flask_session import Session
import re, datetime




app = Flask(__name__)
application = app


app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = "efd432e0aca715610c505c533037b95d6fb22f5692a0d33820ab7b19ef06f513"

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


# Home page
@app.route('/')
def index():

    posts = db.execute("select title, slug, body, name, date_published  from posts, users where users.user_id=posts.author").fetchall()
    return render_template('index.html', posts=posts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = db.execute("select * from users where username= :username", {"username": username})

        user_info = []
        for user in users:
            user_info = list(user)
        
        if username in user_info and password in user_info:
            session['Logged_in'] = True
            session['username'] = username
            session['name'] = user_info[1]
            session['email'] = user_info[3]
            flash('Log in Successful')
            return redirect(url_for('index'))
        else:
            flash('Username or Password incorrect')
            return redirect(url_for('login'))
    
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.pop('username', None)
    session['Logged_in'] = False
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
            db.execute("insert into users(name, username, email, password) values(:name, :username, :email, :password)", {"name": name, "username": username, "email": email, "password": password})
            db.commit()
            return redirect(url_for('login'))
        except exc.IntegrityError:
            flash('Username Already exists, please try another')
            return redirect(url_for('signup'))
    return render_template('signup.html')
        


@app.route('/profile')
def profile():
    try:    
        if session['Logged_in']:
            username = session['username']
            name = session['name']
            email = session['email']

            posts = db.execute("select title, slug, body, date_published, name from posts, users where users.user_id=posts.author and users.username = :username;",{"username": username})
            return render_template('profile.html', username=username, name=name, email=email, posts=posts)
    except KeyError:
        return redirect(url_for('login'))
    return redirect(url_for('login'))
    

@app.route('/edit_post', methods = ['POST', 'GET'])
def edit_post():
    if request.method == 'POST':
        username = session['username']
        post_title = request.form['post_title']
        post_body = request.form['post_body']
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', post_title.lower()) 
        author = db.execute("select user_id from users where username = :username", {"username": username}).fetchone()[0]

        db.execute("insert into posts(title, slug, body, author) values(:post_title, :slug, :post_body, :author)", 
        {"post_title": post_title, "slug": slug,"post_body": post_body, "author": author})
        db.commit()

        return redirect(url_for('profile'))
    return render_template('edit_post.html')



@app.shell_context_processor
def make_shell_context():
    return {'db': db}

if __name__ == "__main__":
    app.run(debug=True)