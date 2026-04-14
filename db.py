import pymysql
from config import Config

def get_connection():
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        port=Config.MYSQL_PORT,  # 🔥 IMPORTANT
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,

        # SSL handling
        ssl=Config.MYSQL_SSL if hasattr(Config, "MYSQL_SSL") else None
    )

    # Initialize tables (only once effectively)
    initialize_database(conn)

    return conn

def initialize_database(conn):
    cursor = conn.cursor()

    # ================= USERS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('shopkeeper', 'farmer') NOT NULL,
        name VARCHAR(255) NOT NULL,
        phone VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_email (email),
        INDEX idx_role (role)
    )
    """)

    # ================= SHOPS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shops (
        id INT AUTO_INCREMENT PRIMARY KEY,
        owner_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        address TEXT,
        phone VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_owner (owner_id)
    )
    """)

    # ================= FERTILIZERS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fertilizers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        unit VARCHAR(50) DEFAULT 'kg',
        category VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_name (name)
    )
    """)

    # ================= INVENTORY =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_inventory (
        id INT AUTO_INCREMENT PRIMARY KEY,
        shop_id INT NOT NULL,
        fertilizer_id INT NOT NULL,
        quantity DECIMAL(12,2) NOT NULL DEFAULT 0,
        price_per_unit DECIMAL(12,2) NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_shop_fertilizer (shop_id, fertilizer_id),
        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
        FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(id) ON DELETE CASCADE,
        INDEX idx_shop (shop_id)
    )
    """)

    # ================= BILLS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INT AUTO_INCREMENT PRIMARY KEY,
        shop_id INT NOT NULL,
        bill_type ENUM('purchase', 'sale') NOT NULL,
        image_path VARCHAR(512),
        extracted_json TEXT,
        total_amount DECIMAL(12,2),
        status ENUM('pending', 'processed', 'failed') DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
        INDEX idx_shop_created (shop_id, created_at)
    )
    """)

    # ================= BILL ITEMS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bill_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        bill_id INT NOT NULL,
        fertilizer_id INT NOT NULL,
        quantity DECIMAL(12,2) NOT NULL,
        price_per_unit DECIMAL(12,2),
        total_price DECIMAL(12,2),
        FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
        FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(id),
        INDEX idx_bill (bill_id)
    )
    """)

    # ================= TRANSACTIONS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        shop_id INT NOT NULL,
        farmer_id INT NULL,
        amount DECIMAL(12,2) NOT NULL,
        payment_method VARCHAR(50) DEFAULT 'upi_demo',
        status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (shop_id) REFERENCES shops(id),
        FOREIGN KEY (farmer_id) REFERENCES users(id),
        INDEX idx_shop_created (shop_id, created_at),
        INDEX idx_farmer_created (farmer_id, created_at)
    )
    """)

    # ================= TRANSACTION ITEMS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        transaction_id INT NOT NULL,
        fertilizer_id INT NOT NULL,
        quantity DECIMAL(12,2) NOT NULL,
        price_per_unit DECIMAL(12,2) NOT NULL,
        total_price DECIMAL(12,2) NOT NULL,
        FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
        FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(id)
    )
    """)

    # ================= ALERTS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        shop_id INT NOT NULL,
        message TEXT NOT NULL,
        alert_type ENUM('low_stock', 'system') DEFAULT 'low_stock',
        is_read TINYINT(1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
        INDEX idx_shop_unread (shop_id, is_read)
    )
    """)

    # ================= SEED DATA =================

    # Admin
    cursor.execute("""
    INSERT IGNORE INTO users (email, password_hash, role, name, phone)
    VALUES ('admin@agromart.com',
    '$2b$12$b7mVqjhDGbgKFEtRxcmeq.gLDIygGtyCRLwy2boSx4YmR/jN9xf1i',
    'shopkeeper', 'Admin', '')
    """)

    # Get admin id safely
    cursor.execute("SELECT id FROM users WHERE email='admin@agromart.com' LIMIT 1")
    admin = cursor.fetchone()

    if admin:
        cursor.execute("""
        INSERT INTO shops (owner_id, name, address, phone)
        SELECT %s, 'Admin Shop', '', ''
        WHERE NOT EXISTS (
            SELECT 1 FROM shops WHERE owner_id = %s
        )
        """, (admin["id"], admin["id"]))

    # Walk-in user
    cursor.execute("""
    INSERT IGNORE INTO users (email, password_hash, role, name, phone)
    VALUES ('walkin@agromart.local',
    '$2b$12$b7mVqjhDGbgKFEtRxcmeq.gLDIygGtyCRLwy2boSx4YmR/jN9xf1i',
    'farmer', 'Walk-in Customer', '')
    """)

    conn.commit()


def dict_cursor(conn):
    return conn.cursor(pymysql.cursors.DictCursor)