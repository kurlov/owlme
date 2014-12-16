from datetime import datetime
from app import app, db, lm, oid
from app.forms import LoginForm, EditForm, PostForm
from app.models import User, Trusted, Post
from app.oauth import OAuthSignIn
from flask import render_template, flash, redirect, g, url_for, session, request
from flask.ext.login import login_user, current_user, logout_user, login_required


@app.route('/')
@app.route('/index')
def index():
    user = g.user
    return render_template('index.html',
                           title="Home",
                           user=user)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])
    return render_template('login.html',
                           title='Sign In',
                           form=form,
                           providers=app.config['OPENID_PROVIDERS'])

@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        trusted = Trusted.query.filter_by(email=email).first()
        if trusted:
            user = User(social_id=social_id, nickname=username, email=email)
            db.session.add(user)
            db.session.commit()
        else:
            flash("Oops, Seems like you are not in the file. Please, contact the site administration.")
            return redirect(url_for('index'))
    login_user(user, True)
    return redirect(url_for('user', nickname=g.user.nickname))

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()

@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()

@app.route('/user/<nickname>')
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    posts = Post.query.all()
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    if user == None:
        flash('User %s not found.' % nickname)
        return redirect(url_for('index'))

    return render_template('user.html',
                           user=user,
                           posts=posts)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditForm()
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.about_me = form.about_me.data
        db.session.add(g.user)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit'))
    else:
        form.nickname.data = g.user.nickname
        form.about_me.data = g.user.about_me
    return render_template('edit.html', form=form)

@app.route('/news', methods=['GET', 'POST'])
@login_required
def news():
    form = PostForm()
    posts = Post.query.all()
    if form.validate_on_submit():
        post = Post(body=form.text, timestamp=datetime.utcnow(), user_id=g.user.id)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been posted .')
        return redirect(url_for('news'))
    return render_template('news.html', form=form, posts=posts)

@app.route('/contacts')
def contacts():
    return render_template('contacts.html', title="Contacts")

@app.route('/about_us')
def about_us():
    return render_template('about_us.html', title="About us")

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        user = User(nickname=nickname, email=resp.email)
        db.session.add(user)
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember = remember_me)
    return redirect(request.args.get('next') or url_for('index'))