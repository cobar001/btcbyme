from typing import NamedTuple
from dateutil import tz
import base64
from enum import Enum
from haversine import haversine
import math
import uuid

from flask import url_for
from btcbyme import geocoder, cg
from btcbyme.models import User, Post


SUPPORTED_CURRENCIES = ['USD', 'EUR', 'CAD', 'GBP', 'JPY']
SUPPORTED_CURRENCIES_SYMBOLS = {'USD': '$', 'EUR': '€', 'CAD': 'CA$', 'GBP': '£', 'JPY': '¥'}
MAX_POST_COUNT_PER_USER = 10
MAX_USER_COUNT_PER_IP = 10
MILES_PER_KILOMETER = 0.6213712
EARTH_RADIUS_KM = 6378
SEARCH_SORTING_OPTIONS = ['Markup: Low to High', 'Markup: High to Low', 'Newest to Oldest', 'Shortest Distance']
POST_PRICE_USD = 3.99
ACCEPTED_BTCPAY_SERVER_TX_STATUS = ['paid', 'complete', 'confirmed']


class PostViewData(NamedTuple):
    btc_price: str
    currency: str
    author_username: str
    markup_percentage: str
    min_tx: str
    max_tx: str
    city: str
    date_posted: str
    id: str
    post_url: str


class GeocodedPostData(NamedTuple):
    lon: float
    lat: float
    place_name: str


class MessageThreadViewData(NamedTuple):
    date_updated_local: str
    sender_id: str
    sender_username: str
    recipient_id: str
    recipient_username: str
    post_url: str
    id: str


class MessageViewData(NamedTuple):
    content: str
    sender_username: str
    date_sent_local: str


class UserViewData(NamedTuple):
    username: str
    local_date_created: str


class BtcPriceData(NamedTuple):
    price_usd: float
    price_eur: float
    price_cad: float
    price_gbp: float
    price_jpy: float


class LatLonBoundingBox(NamedTuple):
    max_lat: float
    min_lat: float
    max_lon: float
    min_lon: float


class SearchSortingOptions(Enum):
    MARKUP_LOW_HIGH = 1
    MARKUP_HIGH_LOW = 2
    DATE_NEW_OLD = 3
    DISTANCE_LOW_HIGH = 4


def format_price(price):
    rounded = '{:0.2f}'.format(price)
    decimal_split = rounded.split('.')
    before_decimal_with_commas = '{:,}'.format(float(decimal_split[0])).split('.')[0]
    return '.'.join([before_decimal_with_commas, decimal_split[-1]])


def format_percentage(percentage):
    return '{:0.2f}'.format(percentage) + '%'


def get_geocoded_post_info(query_string):
    response = geocoder.forward(query_string)
    if not response.ok:
        print(f'Forward geocoding failed:{response.reason}')
        return
    response = response.json()
    if not len(response['features']):
        print('No valid search results for that input.')
        return
    first_feature = response['features'][0]
    center = first_feature['center']
    lon, lat = float(center[0]), float(center[1])
    place_name = first_feature['place_name']
    return GeocodedPostData(lon, lat, place_name)


def utc_to_local_time(datetime_utc):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    datetime_utc = datetime_utc.replace(tzinfo=from_zone)
    return datetime_utc.astimezone(to_zone)


def get_btc_price_from_data(btc_price_data, currency):
    if currency == 'EUR':
        return btc_price_data.price_eur
    elif currency == 'CAD':
        return btc_price_data.price_cad
    elif currency == 'GBP':
        return btc_price_data.price_gbp
    elif currency == 'JPY':
        return btc_price_data.price_jpy
    else:
        return btc_price_data.price_usd


def get_posts_view_data(posts, btc_price_data=None):
    posts_output = []
    btc_price_data = get_btc_price_per_currency() if btc_price_data is None else btc_price_data
    for post in posts:
        price_symbol = SUPPORTED_CURRENCIES_SYMBOLS[post.currency]
        original_price = get_btc_price_from_data(btc_price_data, price_symbol)
        formatted_marked_up_btc_price = price_symbol + format_price(
            original_price + (post.markup / 100 * original_price))
        formatted_local_datetime = post.date_posted.strftime('%Y-%m-%d') + ' UTC'
        post_url = url_for('posts.view_post', post_id=post.id)
        post_author = "username" if post.author is None else post.author.username
        posts_output.append(
            PostViewData(
                formatted_marked_up_btc_price, post.currency, post_author,
                format_percentage(post.markup), price_symbol + format_price(post.min_tx),
                price_symbol + format_price(post.max_tx), post.city, formatted_local_datetime, post.id,
                post_url))
    return posts_output


def get_user_view_data(user):
    return UserViewData(user.username, user.date_created.strftime('%Y-%m-%d') + ' UTC')


def get_btc_price_per_currency():
    prices_result = cg.get_price(
        ids='bitcoin', vs_currencies=','.join([symbol.lower() for symbol in SUPPORTED_CURRENCIES]))
    return BtcPriceData(
        prices_result['bitcoin']['usd'], prices_result['bitcoin']['eur'],
        prices_result['bitcoin']['cad'], prices_result['bitcoin']['gbp'],
        prices_result['bitcoin']['jpy'])


def get_message_thread_view_data(message_threads):
    output_message_threads_view_data = []
    for thread in message_threads:
        sender_username = User.query.filter_by(id=thread.sender_id).first().username
        recipient_username = User.query.filter_by(id=thread.recipient_id).first().username
        post_url = url_for('posts.view_post', post_id=thread.post_id)
        output_message_threads_view_data.append(MessageThreadViewData(
            thread.date_updated.strftime('%c') + ' UTC',
            thread.sender_id, sender_username, thread.recipient_id,
            recipient_username, post_url, thread.id))
    return output_message_threads_view_data


def process_messages_data(messages, thread_view_data=None):
    output_message_view_data = []
    for message in messages:
        message_sender_username = None
        if thread_view_data:
            sender_id, recipient_id = thread_view_data.sender_id, thread_view_data.recipient_id
            sender_username, recipient_username = thread_view_data.sender_username, thread_view_data.recipient_username
            message_sender_username = sender_username if message.sender_id == sender_id else recipient_username
        else:
            message_sender_username = User.query.filter_by(id=message.sender_id).first().username
        local_datetime = message.date_sent.strftime('%c') + ' UTC'
        output_message_view_data.append(MessageViewData(message.content, message_sender_username, local_datetime))
    return output_message_view_data


def create_uuid():
    return str(uuid.uuid4())


def encode_post_data(post):
    post_data = [post.id, post.markup, post.min_tx, post.max_tx, post.latitude,
                 post.longitude, post.currency, post.user_id, post.city]
    string_post_data = [str(data) for data in post_data]
    encoded_data = base64.urlsafe_b64encode(','.join(string_post_data).encode()).decode()
    attempts, max_tries = 0, 4
    while ',' in encoded_data and attempts < max_tries:
        encoded_data = base64.urlsafe_b64encode(','.join(string_post_data).encode()).decode()
        attempts += 1
    if ',' in encoded_data:
        return None
    return encoded_data


def decode_post_data(encoded_post):
    decoded_post_data = base64.urlsafe_b64decode(encoded_post.encode()).decode().split(',')
    city = ', '.join(decoded_post_data[8:])
    return Post(
        id=decoded_post_data[0], markup=float(decoded_post_data[1]), min_tx=float(decoded_post_data[2]),
        max_tx=float(decoded_post_data[3]), latitude=float(decoded_post_data[4]), longitude=float(decoded_post_data[5]),
        city=city, currency=decoded_post_data[6], user_id=decoded_post_data[7])


def get_lat_lon_bounding_box(center_lat, center_lon, box_height_miles):
    dx = dy = box_height_miles / MILES_PER_KILOMETER / 2
    max_lat = center_lat + (dy / EARTH_RADIUS_KM) * (180 / math.pi)
    min_lat = center_lat - (dy / EARTH_RADIUS_KM) * (180 / math.pi)
    max_lon = center_lon + (dx / EARTH_RADIUS_KM) * (180 / math.pi) / math.cos(center_lat * math.pi / 180)
    min_lon = center_lon - (dx / EARTH_RADIUS_KM) * (180 / math.pi) / math.cos(center_lat * math.pi / 180)
    return LatLonBoundingBox(max_lat, min_lat, max_lon, min_lon)


def sort_posts(sorting_enum, posts, geocoded_post_data=None):
    if sorting_enum == SearchSortingOptions.MARKUP_LOW_HIGH:
        posts.sort(key=lambda post: post.markup)
    elif sorting_enum == SearchSortingOptions.MARKUP_HIGH_LOW:
        posts.sort(key=lambda post: post.markup, reverse=True)
    elif sorting_enum == SearchSortingOptions.DATE_NEW_OLD:
        posts.sort(key=lambda post: post.date_posted, reverse=True)
    elif sorting_enum == SearchSortingOptions.DISTANCE_LOW_HIGH:
        if geocoded_post_data is not None:
            posts.sort(key=lambda post: haversine(
                (post.latitude, post.longitude), (geocoded_post_data.lat, geocoded_post_data.lon)))
        else:
            print('DISTANCE_LOW_HIGH sorting enum specified, but no geocoded data was provided.')
    else:
        print('Invalid sorting_enum.')
