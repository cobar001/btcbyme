from flask import Flask
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from btcbyme.config import Config
from btcbyme.utilities import secrets
from pycoingecko import CoinGeckoAPI
from mapbox import Geocoder


db = SQLAlchemy()
cg = CoinGeckoAPI()
bcrypt = Bcrypt()
geocoder = Geocoder(access_token=secrets.MAPBOX_ACCESS_TOKEN)
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    from btcbyme.index.routes import index
    from btcbyme.users.routes import users
    from btcbyme.messages.routes import messages
    from btcbyme.posts.routes import posts

    app.register_blueprint(index)
    app.register_blueprint(users)
    app.register_blueprint(messages)
    app.register_blueprint(posts)

    return app
