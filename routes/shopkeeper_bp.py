from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from db import get_connection
from config import Config

shopkeeper_bp = Blueprint('shopkeeper', __name__)

def shopkeeper_only(f):
    from functools import wraps
    @wraps(f)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return inner

@shopkeeper_bp.route('/dashboard')
@login_required
@shopkeeper_only
def dashboard():
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT name, address, phone FROM shops WHERE id = %s', (shop_id,))
            shop = cur.fetchone()
            cur.execute('''
                SELECT f.name, si.quantity, si.price_per_unit, f.unit
                FROM shop_inventory si JOIN fertilizers f ON f.id = si.fertilizer_id
                WHERE si.shop_id = %s AND si.quantity <= %s
            ''', (shop_id, Config.LOW_STOCK_THRESHOLD))
            low_stock = cur.fetchall()
            cur.execute('''
                SELECT COUNT(*) as c FROM transactions WHERE shop_id = %s AND DATE(created_at) = CURDATE()
            ''', (shop_id,))
            today_sales = cur.fetchone()['c']
            cur.execute('''
                SELECT SUM(amount) as total FROM transactions WHERE shop_id = %s AND DATE(created_at) = CURDATE()
            ''', (shop_id,))
            today_revenue = (cur.fetchone() or {}).get('total') or 0
            cur.execute('SELECT * FROM alerts WHERE shop_id = %s AND is_read = 0 ORDER BY created_at DESC LIMIT 10', (shop_id,))
            alerts = cur.fetchall()
        return render_template('shopkeeper/dashboard.html', shop=shop, low_stock=low_stock,
                             today_sales=today_sales, today_revenue=today_revenue, alerts=alerts)
    finally:
        conn.close()

@shopkeeper_bp.route('/upload-bill', methods=['GET', 'POST'])
@login_required
@shopkeeper_only
def upload_bill():
    return render_template('shopkeeper/upload_bill.html')

@shopkeeper_bp.route('/inventory')
@login_required
@shopkeeper_only
def inventory():
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT si.id, si.fertilizer_id, f.name, f.unit, si.quantity, si.price_per_unit, si.updated_at
                FROM shop_inventory si JOIN fertilizers f ON f.id = si.fertilizer_id
                WHERE si.shop_id = %s ORDER BY f.name
            ''', (shop_id,))
            items = cur.fetchall()
        return render_template('shopkeeper/inventory.html', items=items)
    finally:
        conn.close()

@shopkeeper_bp.route('/reports')
@login_required
@shopkeeper_only
def reports():
    period = request.args.get('period', 'daily')  # daily, weekly, monthly
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if period == 'daily':
                cur.execute('''
                    SELECT DATE(created_at) as dt, COUNT(*) as orders, COALESCE(SUM(amount),0) as revenue
                    FROM transactions WHERE shop_id = %s AND created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    GROUP BY DATE(created_at) ORDER BY dt DESC
                ''', (shop_id,))
            elif period == 'weekly':
                cur.execute('''
                    SELECT YEARWEEK(created_at) as wk, COUNT(*) as orders, COALESCE(SUM(amount),0) as revenue
                    FROM transactions WHERE shop_id = %s AND created_at >= DATE_SUB(CURDATE(), INTERVAL 12 WEEK)
                    GROUP BY YEARWEEK(created_at) ORDER BY wk DESC
                ''', (shop_id,))
            else:
                cur.execute('''
                    SELECT DATE_FORMAT(created_at, "%%Y-%%m") as mn, COUNT(*) as orders, COALESCE(SUM(amount),0) as revenue
                    FROM transactions WHERE shop_id = %s AND created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                    GROUP BY DATE_FORMAT(created_at, "%%Y-%%m") ORDER BY mn DESC
                ''', (shop_id,))
            report_rows = cur.fetchall()
        return render_template('shopkeeper/reports.html', period=period, report_rows=report_rows)
    finally:
        conn.close()

@shopkeeper_bp.route('/bills')
@login_required
@shopkeeper_only
def bills():
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, bill_type, image_path, total_amount, status, created_at
                FROM bills WHERE shop_id = %s ORDER BY created_at DESC
            ''', (shop_id,))
            bills_list = cur.fetchall()
        return render_template('shopkeeper/bills.html', bills=bills_list)
    finally:
        conn.close()

@shopkeeper_bp.route('/sales')
@login_required
@shopkeeper_only
def sales():
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT t.id, t.amount, t.payment_method, t.status, t.created_at, u.name as customer_name
                FROM transactions t LEFT JOIN users u ON u.id = t.farmer_id
                WHERE t.shop_id = %s ORDER BY t.created_at DESC
            ''', (shop_id,))
            sales_list = cur.fetchall()
        return render_template('shopkeeper/sales.html', sales=sales_list)
    finally:
        conn.close()

@shopkeeper_bp.route('/record-sale', methods=['GET', 'POST'])
@login_required
@shopkeeper_only
def record_sale():
    shop_id = current_user.get_shop_id()
    if request.method == 'POST':
        customer_id = request.form.get('farmer_id', type=int)
        if not customer_id and request.form.get('farmer_id') == '':
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE email = 'walkin@agromart.local' LIMIT 1")
                    r = cur.fetchone()
                    customer_id = r['id'] if r else None
            finally:
                conn.close()
        if not customer_id:
            flash('Select a customer (or Walk-in).', 'danger')
            return redirect(url_for('shopkeeper.record_sale'))
        items = []  # [(fertilizer_id, quantity, price_per_unit), ...]
        for key in request.form:
            if key.startswith('qty_'):
                fid = int(key.replace('qty_', ''))
                qty = request.form.get(key, type=float) or 0
                price = request.form.get('price_%s' % fid, type=float) or 0
                if fid and qty > 0:
                    items.append((fid, qty, price))
        if not items:
            flash('Add at least one item with quantity.', 'danger')
            return redirect(url_for('shopkeeper.record_sale'))
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                total = sum(q * p for (_, q, p) in items)
                cur.execute(
                    'INSERT INTO transactions (shop_id, farmer_id, amount, payment_method, status) VALUES (%s, %s, %s, %s, %s)',
                    (shop_id, customer_id, total, 'cash', 'completed')
                )
                tx_id = cur.lastrowid
                for fid, qty, price in items:
                    cur.execute(
                        'INSERT INTO transaction_items (transaction_id, fertilizer_id, quantity, price_per_unit, total_price) VALUES (%s, %s, %s, %s, %s)',
                        (tx_id, fid, qty, price, qty * price)
                    )
                    cur.execute(
                        'UPDATE shop_inventory SET quantity = quantity - %s WHERE shop_id = %s AND fertilizer_id = %s',
                        (qty, shop_id, fid)
                    )
                conn.commit()
            flash('Sale recorded successfully.', 'success')
            return redirect(url_for('shopkeeper.sales'))
        except Exception as e:
            conn.rollback()
            flash('Error: %s' % str(e), 'danger')
            return redirect(url_for('shopkeeper.record_sale'))
        finally:
            conn.close()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM users WHERE role = 'farmer' ORDER BY (email = 'walkin@agromart.local') DESC, name")
            farmers = cur.fetchall()
            cur.execute('''
                SELECT si.fertilizer_id, f.name, f.unit, si.quantity, si.price_per_unit
                FROM shop_inventory si JOIN fertilizers f ON f.id = si.fertilizer_id
                WHERE si.shop_id = %s AND si.quantity > 0 ORDER BY f.name
            ''', (shop_id,))
            inventory = cur.fetchall()
        return render_template('shopkeeper/record_sale.html', farmers=farmers, inventory=inventory)
    finally:
        conn.close()

@shopkeeper_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@shopkeeper_only
def inventory_add():
    shop_id = current_user.get_shop_id()
    if request.method == 'POST':
        fertilizer_id = request.form.get('fertilizer_id', type=int)
        quantity = request.form.get('quantity', type=float) or 0
        price_per_unit = request.form.get('price_per_unit', type=float) or 0
        if not fertilizer_id or quantity <= 0:
            flash('Select a fertilizer and enter quantity.', 'danger')
            return redirect(url_for('shopkeeper.inventory_add'))
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM shop_inventory WHERE shop_id = %s AND fertilizer_id = %s', (shop_id, fertilizer_id))
                row = cur.fetchone()
                if row:
                    cur.execute('UPDATE shop_inventory SET quantity = quantity + %s, price_per_unit = %s, updated_at = NOW() WHERE id = %s',
                                (quantity, price_per_unit, row['id']))
                else:
                    cur.execute('INSERT INTO shop_inventory (shop_id, fertilizer_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)',
                               (shop_id, fertilizer_id, quantity, price_per_unit))
                conn.commit()
            flash('Stock added successfully.', 'success')
            return redirect(url_for('shopkeeper.inventory'))
        except Exception as e:
            conn.rollback()
            flash('Error: %s' % str(e), 'danger')
        finally:
            conn.close()
        return redirect(url_for('shopkeeper.inventory_add'))
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name, unit FROM fertilizers ORDER BY name')
            fertilizers = cur.fetchall()
        return render_template('shopkeeper/inventory_add.html', fertilizers=fertilizers)
    finally:
        conn.close()

@shopkeeper_bp.route('/inventory/adjust/<int:inv_id>', methods=['GET', 'POST'])
@login_required
@shopkeeper_only
def inventory_adjust(inv_id):
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT si.id, si.fertilizer_id, f.name, f.unit, si.quantity, si.price_per_unit FROM shop_inventory si JOIN fertilizers f ON f.id = si.fertilizer_id WHERE si.id = %s AND si.shop_id = %s', (inv_id, shop_id))
            item = cur.fetchone()
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('shopkeeper.inventory'))
        if request.method == 'POST':
            new_qty = request.form.get('quantity', type=float)
            new_price = request.form.get('price_per_unit', type=float)
            if new_qty is not None and new_qty >= 0:
                with conn.cursor() as cur:
                    cur.execute('UPDATE shop_inventory SET quantity = %s, price_per_unit = %s, updated_at = NOW() WHERE id = %s', (new_qty, new_price or item['price_per_unit'], inv_id))
                    conn.commit()
                flash('Inventory updated.', 'success')
            return redirect(url_for('shopkeeper.inventory'))
        return render_template('shopkeeper/inventory_adjust.html', item=item)
    finally:
        conn.close()

@shopkeeper_bp.route('/alerts/mark-read/<int:aid>')
@login_required
@shopkeeper_only
def mark_alert_read(aid):
    shop_id = current_user.get_shop_id()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE alerts SET is_read = 1 WHERE id = %s AND shop_id = %s', (aid, shop_id))
            conn.commit()
    finally:
        conn.close()
    return redirect(url_for('shopkeeper.dashboard'))
