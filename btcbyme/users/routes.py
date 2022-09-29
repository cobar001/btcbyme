from flask import render_template, Blueprint, flash, redirect, url_for, request
from flask_limiter.util import get_remote_address
from flask_login import login_user, current_user, logout_user, login_required
from btcbyme import db, bcrypt, limiter
from btcbyme.models import User, Message, MessageThread, Post
from btcbyme.users import forms
from btcbyme.utilities import utilities


users = Blueprint('users', __name__)


@users.route('/register', methods=['GET', 'POST'])
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index.home'))
    form = forms.RegistrationForm()
    if form.validate_on_submit():
        remote_ip_address = get_remote_address()
        if User.query.filter_by(remote_ip_address=remote_ip_address).count() == utilities.MAX_USER_COUNT_PER_IP:
            flash(f'Registration Unsuccessful. Maximum number of users met for this IP address {remote_ip_address}.',
                  'danger')
            return redirect(url_for('users.register'))
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(id=utilities.create_uuid(), username=form.username.data,
                        password=hashed_password, remote_ip_address=remote_ip_address)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)


@users.route('/login', methods=['GET', 'POST'])
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index.home'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index.home'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Log In', form=form)


@users.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index.home'))


@users.route('/users/delete')
@login_required
def delete():
    user_message_threads = MessageThread.query.filter(
        (MessageThread.sender_id == current_user.get_id()) |
        (MessageThread.recipient_id == current_user.get_id())
    ).all()
    for thread in user_message_threads:
        thread_messages = Message.query.filter_by(thread_id=thread.id).all()
        for message in thread_messages:
            db.session.delete(message)
        db.session.delete(thread)
    user_posts = Post.query.filter_by(
        user_id=current_user.get_id()).order_by(Post.date_posted.desc())
    for post in user_posts:
        db.session.delete(post)
    user = User.query.get_or_404(current_user.get_id())
    db.session.delete(user)
    db.session.commit()
    flash(f'Your account has been successfully deleted!', 'success')
    return redirect(url_for('users.register'))


@users.route('/account')
@login_required
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def account():
    user_view_data = utilities.get_user_view_data(User.query.filter_by(id=current_user.get_id()).first())
    user_posts = Post.query.filter_by(
        user_id=current_user.get_id()).order_by(Post.date_posted.desc()).all()
    user_posts_view_data = None if len(user_posts) == 0 else utilities.get_posts_view_data(user_posts)
    message_threads = MessageThread.query.filter(
        (MessageThread.sender_id == current_user.get_id()) |
        (MessageThread.recipient_id == current_user.get_id())
    ).order_by(MessageThread.date_updated.desc()).all()
    message_threads_view_data = utilities.get_message_thread_view_data(message_threads)
    return render_template(
        'account.html', title='Account', user_view_data=user_view_data, user_posts=user_posts_view_data,
        message_threads=message_threads_view_data)
