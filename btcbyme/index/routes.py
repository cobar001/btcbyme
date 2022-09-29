from btcbyme.models import Post
from flask import render_template, Blueprint
from btcbyme import limiter
from btcbyme.utilities import utilities


index = Blueprint('index', __name__)


@index.route('/')
@index.route('/home')
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def home():
    posts = Post.query.order_by(Post.date_posted.desc()).limit(12).all()
    posts_view_data = utilities.get_posts_view_data(posts)
    return render_template(
        'index.html', title='Home', posts=posts_view_data,
        supported_currencies=utilities.SUPPORTED_CURRENCIES)


@index.route('/about')
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def about():
    return render_template('about.html', title='About')


@index.route('/how_it_works')
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def how_it_works():
    return render_template('how_it_works.html', title='How?')


@index.route('/terms')
@limiter.limit('500/day; 100/hour;', override_defaults=True)
def terms_of_service():
    return render_template('terms.html', title='Terms')
