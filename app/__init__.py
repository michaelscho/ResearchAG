from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

csrf = CSRFProtect()
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')  # Load configuration

    # Initialize database, login manager, and CSRF protection
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader function for Flask-Login
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = 'routes.login'

    # Initialize caching structure for LLMs, chains, etc.
    app.config['CACHE'] = {}  # Create an empty dictionary to store reusable objects

    with app.app_context():
        db.create_all()

    # Register routes
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    print(app.url_map)

    return app
