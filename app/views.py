from datetime import datetime
from app import app, db, lm, oid
from app.forms import LoginForm, EditForm, PostForm, SearchForm
from app.models import User, Trusted, Post
from app.oauth import OAuthSignIn
from config import MAX_SEARCH_RESULTS
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

@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous():
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, nickname, email = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        trusted = Trusted.query.filter_by(email=email).first()
        if trusted:
            nickname = User.make_unique_nickname(nickname)
            user = User(social_id=social_id, nickname=nickname, email=email)
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
        g.search_form = SearchForm()

@app.route('/user/<nickname>')
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    posts = Post.query.all()
    if user == None:
        flash('User %s not found.' % nickname)
        return redirect(url_for('index'))

    return render_template('user.html',
                           user=user,
                           posts=posts)

@app.route('/map')
@login_required
def map():
    coords = [[56.849579, 60.647686]]
    return render_template('map.html',
                           coords=coords)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.nickname)
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
        post = Post(body=form.text.data, timestamp=datetime.utcnow(), author=g.user)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('news'))
    return render_template('news.html', form=form, posts=posts)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    results = []
    if g.search_form.validate_on_submit():
        query=g.search_form.text.data
        results = User.query.whoosh_search(query, MAX_SEARCH_RESULTS).all()
    return render_template('search.html',
                            results=results)

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