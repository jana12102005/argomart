from flask import Blueprint, render_template
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('main/index.html', current_user=current_user)

@main_bp.route('/about')
def about():
    return render_template('main/about.html', current_user=current_user)

@main_bp.route('/services')
def services():
    return render_template('main/services.html', current_user=current_user)

@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html', current_user=current_user)
