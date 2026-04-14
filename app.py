# AgroHands AI / Agromart - Main Flask Application
import os
from flask import Flask, send_from_directory
from flask_login import LoginManager

from config import Config
from auth import User

# Flask app
app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# Serve assets from /assets
@app.route('/assets/<path:path>')
def asset(path):
    return send_from_directory(os.path.join(app.root_path, 'assets'), path)

# Login manager
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

# Ensure uploads folder exists
Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Disable caching for authenticated pages
@app.after_request
def add_cache_control_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Local development only
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
