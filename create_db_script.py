import uuid

from btcbyme.models import User, Post, Message, MessageThread
from btcbyme import db, create_app, bcrypt
from btcbyme.utilities import utilities

app = create_app()
app.app_context().push()
db.create_all(app=app)

test_usernames = ['ccobar', 'cobar70', 'cobar001', 'test_user_test']
test_uids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]
test_ips = ['127.0.0.1', '127.0.0.2', '127.0.0.3', '127.0.0.4']

test_posts_markups = [10.0, 23.3, 3.3, 1.2, 4.5, 7.8, 5.6, 2.2]
test_posts_tx_limits = [[0, 500], [0, 400], [0, 2500], [40, 500],
                        [10, 50], [30, 50430], [2, 700], [0, 500]]
test_posts_locations = [
    'Rosevillle,Minnesota,United States',
    'Shoreview,Minnesota,United States',
    'Minneapolis,Minnesota,United States',
    'Edina,Minnesota,United States',
    'Minneapolis,Minnesota,United States',
    'Minneapolis,Minnesota,United States',
    'Mountain View,California,United States',
    'Palo Alto,California,United States'
]

hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
for i, username in enumerate(test_usernames):
    new_user = User(id=test_uids[i], username=username, password=hashed_password, remote_ip_address=test_ips[i])
    db.session.add(new_user)

test_post_id = str(uuid.uuid4())
for i in range(len(test_posts_locations)):
    geocoded_post_data = utilities.get_geocoded_post_info(test_posts_locations[i])
    tx_limits = test_posts_tx_limits[i]
    new_post = Post(
        id=str(uuid.uuid4()) if i != 0 else test_post_id,
        markup=test_posts_markups[i], min_tx=test_posts_tx_limits[i][0],
        max_tx=test_posts_tx_limits[i][1], latitude=geocoded_post_data.lat,
        longitude=geocoded_post_data.lon, city=geocoded_post_data.place_name,
        user_id=test_uids[i % len(test_usernames)], currency='USD')
    db.session.add(new_post)

thread_uid = str(uuid.uuid4())
new_thread = MessageThread(id=thread_uid, sender_id=test_uids[1], recipient_id=test_uids[0], post_id=test_post_id)
new_message = Message(id=str(uuid.uuid4()), recipient_id=test_uids[0], sender_id=test_uids[1],
                      content='Hello, how are you today?', thread_id=thread_uid)
new_message2 = Message(id=str(uuid.uuid4()), recipient_id=test_uids[1], sender_id=test_uids[0],
                       content='Im doing well, and yourself?', thread_id=thread_uid)
new_message3 = Message(id=str(uuid.uuid4()), recipient_id=test_uids[0], sender_id=test_uids[1],
                       content='Im also doing well. Would you like to sell some btc?', thread_id=thread_uid)
new_message4 = Message(id=str(uuid.uuid4()), recipient_id=test_uids[1], sender_id=test_uids[0],
                       content='Yes, lets do it.', thread_id=thread_uid)
db.session.add(new_thread)
db.session.add(new_message)
db.session.add(new_message2)
db.session.add(new_message3)
db.session.add(new_message4)

db.session.commit()

# https://github.com/btcpayserver/btcpay-python
