# API: OCR, inventory update, reports data
import json
import os
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
from db import get_connection
from services.ocr_service import process_bill_image, allowed_file

api_bp = Blueprint('api', __name__)

def shopkeeper_required(f):
    from functools import wraps
    @wraps(f)
    def inner(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            return jsonify({'error': 'Shopkeeper access required'}), 403
        return f(*args, **kwargs)
    return inner

@api_bp.route('/ocr/extract', methods=['POST'])
@login_required
@shopkeeper_required
def ocr_extract():
    if 'bill_image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['bill_image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename, {'png', 'jpg', 'jpeg'}):
        return jsonify({'error': 'Allowed: png, jpg, jpeg'}), 400
    filename = secure_filename(file.filename)
    save_path = Config.UPLOAD_FOLDER / f"{current_user.id}_{os.urandom(8).hex()}_{filename}"
    file.save(str(save_path))
    try:
        result = process_bill_image(save_path)
        return jsonify({'items': result['items'], 'lines': result.get('lines', []), 'image_path': str(save_path)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/inventory/update-from-bill', methods=['POST'])
@login_required
@shopkeeper_required
def update_inventory_from_bill():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    bill_type = data.get('bill_type', 'purchase')  # purchase | sale
    items = data.get('items', [])  # [{ fertilizer_id, quantity, price_per_unit }]
    image_path = data.get('image_path', '')
    shop_id = current_user.get_shop_id()
    if not shop_id:
        return jsonify({'error': 'Shop not found'}), 400
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO bills (shop_id, bill_type, image_path, status) VALUES (%s, %s, %s, %s)',
                (shop_id, bill_type, image_path, 'processed')
            )
            bill_id = cur.lastrowid
            total = 0
            for it in items:
                fid = it.get('fertilizer_id')
                qty = float(it.get('quantity', 0))
                price = float(it.get('price_per_unit', 0))
                if fid and qty:
                    cur.execute(
                        'SELECT id, quantity FROM shop_inventory WHERE shop_id = %s AND fertilizer_id = %s',
                        (shop_id, fid)
                    )
                    row = cur.fetchone()
                    if row:
                        existing_qty = float(row['quantity']) if row['quantity'] is not None else 0.0
                        new_qty = existing_qty + (qty if bill_type == 'purchase' else -qty)
                        new_qty = max(0, new_qty)
                        cur.execute(
                            'UPDATE shop_inventory SET quantity = %s, price_per_unit = %s, updated_at = NOW() WHERE id = %s',
                            (new_qty, price or row.get('price_per_unit', 0), row['id'])
                        )
                    else:
                        if bill_type == 'purchase':
                            cur.execute(
                                'INSERT INTO shop_inventory (shop_id, fertilizer_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)',
                                (shop_id, fid, qty, price)
                            )
                    cur.execute(
                        'INSERT INTO bill_items (bill_id, fertilizer_id, quantity, price_per_unit, total_price) VALUES (%s, %s, %s, %s, %s)',
                        (bill_id, fid, qty, price, qty * price)
                    )
                    total += qty * price
            cur.execute('UPDATE bills SET total_amount = %s WHERE id = %s', (total, bill_id))
            # Low stock alerts
            cur.execute('''
                INSERT INTO alerts (shop_id, message, alert_type)
                SELECT %s, CONCAT("Low stock: ", f.name, " (", si.quantity, " ", f.unit, ")"), "low_stock"
                FROM shop_inventory si
                JOIN fertilizers f ON f.id = si.fertilizer_id
                WHERE si.shop_id = %s AND si.quantity <= %s
            ''', (shop_id, shop_id, Config.LOW_STOCK_THRESHOLD))
            conn.commit()
        return jsonify({'success': True, 'bill_id': bill_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/fertilizers/search')
def fertilizers_search():
    q = request.args.get('q', '').strip()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if q:
                cur.execute('SELECT id, name, unit, category FROM fertilizers WHERE name LIKE %s ORDER BY name', (f'%{q}%',))
            else:
                cur.execute('SELECT id, name, unit, category FROM fertilizers ORDER BY name')
            rows = cur.fetchall()
        return jsonify({'fertilizers': rows})
    finally:
        conn.close()
