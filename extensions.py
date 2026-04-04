from flask_caching import Cache
from flask_login import LoginManager
from models import db

# We import db here to easily gather all extensions in one place,
# though it's technically instantiated in models.py
cache = Cache()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
