from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from db import get_connection

farmer_bp = Blueprint('farmer', __name__)

def farmer_only(f):
    from functools import wraps
    @wraps(f)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'farmer':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return inner

@farmer_bp.route('/dashboard')
@login_required
@farmer_only
def dashboard():
    return render_template('farmer/dashboard.html')

@farmer_bp.route('/shops')
@login_required
@farmer_only
def shops():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT s.id, s.name, s.address, s.phone, u.name as owner_name
                FROM shops s JOIN users u ON u.id = s.owner_id ORDER BY s.name
            ''')
            shops_list = cur.fetchall()
        return render_template('farmer/shops.html', shops=shops_list)
    finally:
        conn.close()

@farmer_bp.route('/shop/<int:shop_id>')
@login_required
@farmer_only
def shop_products(shop_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, address, phone FROM shops WHERE id = %s', (shop_id,))
            shop = cur.fetchone()
            if not shop:
                flash('Shop not found.', 'danger')
                return redirect(url_for('farmer.shops'))
            cur.execute('''
                SELECT si.fertilizer_id, f.name, f.unit, si.quantity, si.price_per_unit
                FROM shop_inventory si JOIN fertilizers f ON f.id = si.fertilizer_id
                WHERE si.shop_id = %s AND si.quantity > 0 ORDER BY f.name
            ''', (shop_id,))
            products = cur.fetchall()
        return render_template('farmer/shop_products.html', shop=shop, products=products)
    finally:
        conn.close()

def _cart_key(shop_id):
    """Use string keys so session (JSON) serialization doesn't mix int/str."""
    return str(shop_id) if shop_id is not None else None

@farmer_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@farmer_only
def checkout():
    if request.method == 'POST':
        # Dummy UPI: accept and create transaction
        shop_id = request.form.get('shop_id', type=int)
        cart = session.get('cart', {})  # keys are str(shop_id)
        items = cart.get(_cart_key(shop_id), [])
        if not shop_id or not items:
            flash('Cart is empty.', 'danger')
            return redirect(url_for('farmer.dashboard'))
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                total = sum(float(i.get('quantity', 0)) * float(i.get('price_per_unit', 0)) for i in items)
                cur.execute(
                    'INSERT INTO transactions (shop_id, farmer_id, amount, payment_method, status) VALUES (%s, %s, %s, %s, %s)',
                    (shop_id, current_user.id, total, 'upi_demo', 'completed')
                )
                tx_id = cur.lastrowid
                for it in items:
                    fid = it.get('fertilizer_id')
                    qty = float(it.get('quantity', 0))
                    price = float(it.get('price_per_unit', 0))
                    cur.execute(
                        'INSERT INTO transaction_items (transaction_id, fertilizer_id, quantity, price_per_unit, total_price) VALUES (%s, %s, %s, %s, %s)',
                        (tx_id, fid, qty, price, qty * price)
                    )
                    cur.execute(
                        'UPDATE shop_inventory SET quantity = quantity - %s WHERE shop_id = %s AND fertilizer_id = %s',
                        (qty, shop_id, fid)
                    )
                conn.commit()
            session['cart'] = {k: v for k, v in cart.items() if k != _cart_key(shop_id)}
            flash('Payment successful (Demo UPI). Order placed.', 'success')
            return redirect(url_for('farmer.orders'))
        except Exception as e:
            conn.rollback()
            flash(f'Checkout failed: {str(e)}', 'danger')
            return redirect(url_for('farmer.checkout', shop_id=shop_id))
        finally:
            conn.close()
    shop_id = request.args.get('shop_id', type=int)
    cart = session.get('cart', {}).get(_cart_key(shop_id), [])
    shop = None
    total = sum(float(it.get('quantity', 0)) * float(it.get('price_per_unit', 0)) for it in cart)
    if shop_id:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id, name FROM shops WHERE id = %s', (shop_id,))
                shop = cur.fetchone()
        finally:
            conn.close()
    return render_template('farmer/checkout.html', shop=shop, cart=cart, shop_id=shop_id, total=total)

@farmer_bp.route('/add-to-cart', methods=['POST'])
@login_required
@farmer_only
def add_to_cart():
    shop_id = request.form.get('shop_id', type=int)
    fertilizer_id = request.form.get('fertilizer_id', type=int)
    quantity = float(request.form.get('quantity', 0) or 0)
    name = request.form.get('name', '') or ''
    price_per_unit = float(request.form.get('price_per_unit', 0) or 0)
    if not shop_id or not fertilizer_id or quantity <= 0:
        flash('Invalid item or quantity.', 'danger')
        return redirect(request.referrer or url_for('farmer.shops'))
    cart = session.get('cart', {})
    key = _cart_key(shop_id)
    if key not in cart:
        cart[key] = []
    # Merge same product
    found = False
    for it in cart[key]:
        if it.get('fertilizer_id') == fertilizer_id:
            it['quantity'] = float(it.get('quantity', 0)) + quantity
            found = True
            break
    if not found:
        cart[key].append({
            'fertilizer_id': int(fertilizer_id), 'name': name, 'quantity': quantity, 'price_per_unit': price_per_unit
        })
    session['cart'] = cart
    session.modified = True
    flash('Added to cart.', 'success')
    return redirect(request.referrer or url_for('farmer.shops'))

@farmer_bp.route('/orders')
@login_required
@farmer_only
def orders():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT t.id, t.amount, t.payment_method, t.created_at, s.name as shop_name
                FROM transactions t JOIN shops s ON s.id = t.shop_id
                WHERE t.farmer_id = %s ORDER BY t.created_at DESC
            ''', (current_user.id,))
            orders_list = cur.fetchall()
        return render_template('farmer/orders.html', orders=orders_list)
    finally:
        conn.close()