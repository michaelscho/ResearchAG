import os

class Config:
    # Generate a secure secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here'
    WTF_CSRF_ENABLED = True
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'data', 'database.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login settings
    REMEMBER_COOKIE_DURATION = 3600  # Duration in seconds

    # Application-specific settings
    APP_NAME = "Flask App"

    # Enable or disable features (customize as needed)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
