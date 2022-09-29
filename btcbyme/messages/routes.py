from datetime import datetime

from flask import render_template, Blueprint, abort, redirect, url_for, flash
from flask_login import login_required, current_user
from btcbyme import db, limiter
from btcbyme.messages.forms import NewMessageForm
from btcbyme.models import MessageThread, Message, Post
from btcbyme.utilities import utilities


messages = Blueprint('messages', __name__)


@messages.route('/messages')
@login_required
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def index_messages():
    user_message_threads = list(MessageThread.query.filter(
        (MessageThread.sender_id == current_user.get_id()) |
        (MessageThread.recipient_id == current_user.get_id())
    ).order_by(MessageThread.date_updated.desc()))
    user_message_threads_data = utilities.get_message_thread_view_data(user_message_threads)
    return render_template('messages.html', title='Messages', user_message_threads_data=user_message_threads_data)


@messages.route('/messages/new_thread/<string:post_id>', methods=['GET', 'POST'])
@login_required
def new_message_thread(post_id):
    form = NewMessageForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        now_utc = datetime.utcnow()
        new_thread_uuid = utilities.create_uuid()
        new_thread = MessageThread(
            id=new_thread_uuid, date_updated=now_utc, sender_id=current_user.get_id(),
            recipient_id=post.user_id, post_id=post.id)
        new_message = Message(
            id=utilities.create_uuid(),
            recipient_id=post.user_id, sender_id=current_user.get_id(), content=form.content.data,
            thread_id=new_thread_uuid, date_sent=now_utc)
        db.session.add(new_thread)
        db.session.add(new_message)
        db.session.commit()
        return redirect(url_for('messages.message_thread', thread_id=new_thread_uuid))
    post_view_data = utilities.get_posts_view_data([post])[0]
    return render_template('new_thread.html', title='New Thread', post_data=post_view_data, form=form)


@messages.route('/messages/<string:thread_id>', methods=['GET', 'POST'])
@login_required
def message_thread(thread_id):
    thread = MessageThread.query.get_or_404(thread_id)
    if not (current_user.get_id() == str(thread.sender_id) or
            current_user.get_id() == str(thread.recipient_id)):
        abort(403)
    form = NewMessageForm()
    if form.validate_on_submit():
        now_utc = datetime.utcnow()
        new_message = Message(
            id=utilities.create_uuid(),
            recipient_id=thread.recipient_id if current_user.get_id() != thread.recipient_id else thread.sender_id,
            sender_id=current_user.get_id(),
            content=form.content.data, thread_id=thread.id, date_sent=now_utc)
        thread.date_updated = now_utc
        db.session.add(new_message)
        db.session.commit()
        return redirect(url_for('messages.message_thread', thread_id=thread.id))
    thread_data = utilities.get_message_thread_view_data([thread])[0]
    thread_messages = Message.query.filter_by(thread_id=thread.id).order_by(Message.date_sent.asc())
    messages_data = utilities.process_messages_data(thread_messages, thread_data)
    return render_template(
        'thread.html', title=f'Thread {thread.id}', messages_data=messages_data, thread_data=thread_data, form=form)


@messages.route('/messages/<string:thread_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_message_thread(thread_id):
    thread = MessageThread.query.get_or_404(thread_id)
    thread_messages = Message.query.filter_by(thread_id=thread.id)
    if not (current_user.get_id() == thread.sender_id or
            current_user.get_id() == thread.recipient_id):
        abort(403)
    db.session.delete(thread)
    for message in thread_messages:
        db.session.delete(message)
    db.session.commit()
    flash(f'Message thread {thread.id} has been deleted!', 'success')
    return redirect(url_for('messages.index_messages'))
