import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func

# ---------------- Flask Config ----------------
app = Flask(__name__)
app.secret_key = "your_secret_key"




# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///data.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Uploads
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "static", "uploads")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)


# ---------------- Models ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(50), nullable=True)
    image_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")



class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)


#class Like(db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
#
class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # ✅ नया column





# ---------------- Routes ----------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if user:
        if check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Login successful!")
            return redirect(url_for('home'))
        else:
            flash("Wrong password!")
            return redirect(url_for('index'))
    else:
        # auto signup if user does not exist
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        flash("Account created and logged in!")
        return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out!")
    return redirect(url_for('index'))


@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('home.html', posts=posts, title="Home")


@app.route('/our')
def our_posts():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    posts = Post.query.filter_by(user_id=session['user_id']).order_by(Post.created_at.desc()).all()
    return render_template('our.html', posts=posts, title="Our Posts")


@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    post = Post.query.get_or_404(post_id)
    if post.user_id == session['user_id']:
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted successfully!")
    else:
        flash("Unauthorized action!")
    return redirect(url_for('our_posts'))


@app.route('/post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        text = request.form['text']
        tag = request.form['tag']
        file = request.files.get('image')

        filename = None
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_post = Post(text=text, tag=tag, image_filename=filename, user_id=session['user_id'])
        db.session.add(new_post)
        db.session.commit()
        flash("Post created!")
        return redirect(url_for('home'))

    return render_template('post.html')


@app.route('/trending')
def trending():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    hashtags = db.session.query(Post.tag, func.count(Post.id).label('count')).group_by(Post.tag).all()
    return render_template('trending.html', hashtags=hashtags)


@app.route('/hashtag/<tag>')
def hashtag_posts(tag):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    posts = Post.query.filter_by(tag=tag).order_by(Post.created_at.desc()).all()
    return render_template('hashtag_posts.html', posts=posts, tag=tag)


@app.route('/inbox')
def inbox():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    posts = Post.query.filter_by(user_id=session['user_id']).order_by(Post.created_at.desc()).all()
    return render_template('inbox.html', posts=posts)



@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    text = request.form['text']
    new_comment = Comment(text=text, post_id=post_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(request.referrer or url_for('home'))


#@app.route('/like/<int:post_id>', methods=['POST'])
#def add_like(post_id):
#    if 'user_id' not in session:
#        return redirect(url_for('index'))
#    new_like = Like(post_id=post_id)
#    db.session.add(new_like)
#    db.session.commit()
#    return redirect(request.referrer or url_for('home'))

@app.route('/like/<int:post_id>', methods=['POST'])
def add_like(post_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # ✅ check if already liked by this user
    existing_like = Like.query.filter_by(post_id=post_id, user_id=session['user_id']).first()
    if existing_like:
        flash("You already liked this post!")
        return redirect(request.referrer or url_for('home'))

    # ✅ otherwise add new like
    new_like = Like(post_id=post_id, user_id=session['user_id'])
    db.session.add(new_like)
    db.session.commit()
    flash("Post liked!")
    return redirect(request.referrer or url_for('home'))





# ---------------- Run ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()    # ✅ फिर नए schema से बनाओ
    app.run(debug=True)
