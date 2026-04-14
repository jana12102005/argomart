# AgroHands AI / Agromart - Main Flask Application
import os
from flask import Flask, send_from_directory
from flask_login import LoginManager

from config import Config
from auth import User

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# Serve existing assets from project root /assets/...
@app.route('/assets/<path:path>')
def asset(path):
    return send_from_directory(os.path.join(app.root_path, 'assets'), path)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.get(int(user_id))
    except (ValueError, TypeError, Exception):
        return None

# Blueprints
from routes.auth_bp import auth_bp
from routes.main_bp import main_bp
from routes.shopkeeper_bp import shopkeeper_bp
from routes.farmer_bp import farmer_bp
from routes.api_bp import api_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)
app.register_blueprint(shopkeeper_bp, url_prefix='/shopkeeper')
app.register_blueprint(farmer_bp, url_prefix='/farmer')
app.register_blueprint(api_bp, url_prefix='/api')

# Create uploads dir
Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


@app.after_request
def add_cache_control_headers(response):
    """
    Prevent browsers from serving cached versions of authenticated pages.
    This helps ensure that after logout, using the Back button doesn't
    show old dashboard content; the browser must re-request the page and
    Flask-Login will redirect to login if not authenticated.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000)
