from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from db import get_connection
from auth import hash_password, check_password, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated and request.method == 'GET':
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'farmer')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        if not email or not password or not name:
            flash('Email, name and password are required.', 'danger')
            return render_template('auth/register.html')
        if role not in ('shopkeeper', 'farmer'):
            role = 'farmer'
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM users WHERE email = %s', (email,))
                if cur.fetchone():
                    flash('Email already registered.', 'danger')
                    return render_template('auth/register.html')
                pw_hash = hash_password(password)
                cur.execute(
                    'INSERT INTO users (email, password_hash, role, name, phone) VALUES (%s, %s, %s, %s, %s)',
                    (email, pw_hash, role, name, phone)
                )
                user_id = cur.lastrowid
                if role == 'shopkeeper':
                    shop_name = request.form.get('shop_name', name + ' Shop').strip() or (name + ' Shop')
                    shop_address = request.form.get('shop_address', '').strip()
                    cur.execute(
                        'INSERT INTO shops (owner_id, name, address, phone) VALUES (%s, %s, %s, %s)',
                        (user_id, shop_name, shop_address, phone)
                    )
                conn.commit()
            user = User.get(user_id)
            login_user(user)
            flash('Registration successful.', 'success')
            if user.role == 'shopkeeper':
                return redirect(url_for('shopkeeper.dashboard'))
            return redirect(url_for('farmer.dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('auth/register.html')
        finally:
            conn.close()
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Please enter email and password.', 'danger')
            return render_template('auth/login.html')
        try:
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT id, email, password_hash, role, name, phone FROM users WHERE email = %s',
                        (email,)
                    )
                    row = cur.fetchone()
                if not row:
                    flash('Invalid email or password.', 'danger')
                    return render_template('auth/login.html')
                try:
                    if not check_password(password, row['password_hash']):
                        flash('Invalid email or password.', 'danger')
                        return render_template('auth/login.html')
                except Exception as e:
                    flash(f'Password check error: {e}', 'danger')
                    return render_template('auth/login.html')
                user = User(row['id'], row['email'], row['role'], row['name'], row.get('phone') or '', None)
                login_user(user, remember=True)
                flash('Logged in successfully.', 'success')
                next_url = request.args.get('next') or url_for('main.home')
                if user.role == 'shopkeeper':
                    next_url = request.args.get('next') or url_for('shopkeeper.dashboard')
                elif user.role == 'farmer':
                    next_url = request.args.get('next') or url_for('farmer.dashboard')
                return redirect(next_url)
            finally:
                conn.close()
        except Exception as e:
            flash(f'Login failed: {e}', 'danger')
            return render_template('auth/login.html')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))
