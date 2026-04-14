# AgroHands AI – Agromart

Automated fertilizer inventory management for rural shops: **OCR-based bill extraction**, real-time stock updates, low-stock alerts, reports, and **demo UPI** payment for farmers.

## Features

- **Shopkeepers:** Register shop → Upload purchase/sale bills (image) → OCR extracts items → Confirm and apply to inventory. View inventory, daily/weekly/monthly reports, low-stock alerts.
- **Farmers:** Browse shops → View fertilizer availability and prices → Add to cart → Checkout with **demo UPI** (no real payment).
- **Tech:** Flask (Python), MySQL, EasyOCR for bill text extraction, role-based auth (shopkeeper / farmer).

## Requirements

- Python 3.8+
- MySQL 5.7+ (or MariaDB)
- 4 GB RAM, modern browser (Chrome, Edge, Firefox)

## Setup

### 1. Database

Create database and user, then load schema:

```bash
mysql -u root -p -e "CREATE DATABASE agromart;"
mysql -u root -p agromart < schema.sql
```

### 2. Python env and dependencies

```bash
cd "f:\Doc and Code\Python\2026\Agromart OCR Based inventry\Code"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration

Edit `config.py` or set environment variables:

- `MYSQL_HOST` (default: localhost)
- `MYSQL_USER` (default: root)
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE` (default: agromart)

### 4. Run

```bash
python app.py
```

Open **http://127.0.0.1:5000**

- **Register** as Shopkeeper or Farmer.
- Shopkeeper: complete registration (shop name/address optional) → Dashboard → **Upload Bill** (OCR) → Inventory / Reports.
- Farmer: Dashboard → **Shops** → choose shop → add products to cart → **Checkout** (Demo UPI).

## OCR

- **EasyOCR** is used to extract text from bill images. First run may download model files.
- If EasyOCR is not installed, the upload page still works; you get a placeholder line and can add items manually by selecting fertilizer and quantity.
- Supported formats: PNG, JPG, JPEG. Max size: 10 MB.

## Project layout

- `app.py` – Flask app, blueprints, `/assets/` route for static files
- `config.py` – Secret key, MySQL settings, upload path, low-stock threshold
- `db.py` – MySQL connection helper
- `auth.py` – Password hashing, `User` model, `User.get_shop_id()` for shopkeepers
- `schema.sql` – Tables: users, shops, fertilizers, shop_inventory, bills, bill_items, transactions, transaction_items, alerts
- `services/ocr_service.py` – Bill image → text → parsed fertilizer items
- `routes/` – auth_bp, main_bp, shopkeeper_bp, farmer_bp, api_bp (OCR, inventory update, fertilizer search)
- `templates/` – base, auth (login, register), main (index, about, services, contact), shopkeeper (dashboard, upload_bill, inventory, reports), farmer (dashboard, shops, shop_products, checkout, orders)
- `assets/` – CSS/JS/images (existing template assets)
- `uploads/bills/` – Stored bill images (created automatically)

## Security notes

- Set a strong `SECRET_KEY` in production (e.g. via env).
- Use HTTPS and secure cookies in production.
- Demo UPI is for demonstration only; no real payment processing.
