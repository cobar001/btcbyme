from datetime import datetime
from btcbyme import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(str(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.String(120), primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    remote_ip_address = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), unique=True)

    def __repr__(self):
        return f'User {self.id}: {self.username} {self.password}'


class Post(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    markup = db.Column(db.Float, nullable=False)
    min_tx = db.Column(db.Float, nullable=False)
    max_tx = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return (f'Post {self.id}: {self.date_posted} {self.markup} {self.min_tx}' +
                f' {self.max_tx} {self.latitude} {self.longitude} {self.city}' +
                f' {self.user_id} {self.currency}')


class MessageThread(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sender_id = db.Column(db.String(120), nullable=False)
    recipient_id = db.Column(db.String(120), nullable=False)
    post_id = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return (f'MessageThread {self.id} Last updated {self.date_updated} ' +
                f'{self.sender_id} {self.recipient_id} {self.post_id}')


class Message(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    recipient_id = db.Column(db.String(120), nullable=False)
    sender_id = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    thread_id = db.Column(db.String(120), nullable=False)
    date_sent = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (f'Message {self.id} {self.recipient_id} {self.sender_id} ' +
                f'{self.content} {self.thread_id} {self.date_sent}')


class Persistent(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    btcpay_server_client = db.Column(db.PickleType, unique=True)
