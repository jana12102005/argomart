

CREATE DATABASE IF NOT EXISTS agromart;
USE agromart;

SET NAMES utf8mb4;

-- Users: shopkeepers and farmers
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
);

-- Shops (one per shopkeeper)
CREATE TABLE IF NOT EXISTS shops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_owner (owner_id)
);



-- Master list of fertilizer products (can be extended by admin/shopkeeper)
CREATE TABLE IF NOT EXISTS fertilizers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    unit VARCHAR(50) DEFAULT 'kg',
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);

-- Inventory per shop per fertilizer
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
);

-- Bills (purchase or sale) - store image path and extracted data
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
);

-- Line items from a bill (for audit and inventory update source)
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
);

-- Sales transactions (farmer purchases from shop - for reports and history)
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shop_id INT NOT NULL,
    farmer_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'upi_demo',
    status ENUM('pending', 'completed', 'failed') DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    FOREIGN KEY (farmer_id) REFERENCES users(id),
    INDEX idx_shop_created (shop_id, created_at),
    INDEX idx_farmer_created (farmer_id, created_at)
);

-- Transaction line items (what was bought)
CREATE TABLE IF NOT EXISTS transaction_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    fertilizer_id INT NOT NULL,
    quantity DECIMAL(12,2) NOT NULL,
    price_per_unit DECIMAL(12,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(id)
);

-- Low-stock alerts for shopkeepers
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shop_id INT NOT NULL,
    message TEXT NOT NULL,
    alert_type ENUM('low_stock', 'system') DEFAULT 'low_stock',
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    INDEX idx_shop_unread (shop_id, is_read)
);

-- Seed a few default fertilizers for demo
INSERT IGNORE INTO fertilizers (name, unit, category) VALUES
('Urea', 'kg', 'Nitrogen'),
('DAP (Di-Ammonium Phosphate)', 'kg', 'Phosphatic'),
('NPK 19:19:19', 'kg', 'Complex'),
('Potash (MOP)', 'kg', 'Potash'),
('Super Phosphate', 'kg', 'Phosphatic'),
('Ammonium Sulphate', 'kg', 'Nitrogen'),
('Zinc Sulphate', 'kg', 'Micronutrient'),
('Organic Manure', 'kg', 'Organic');

-- Walk-in customer for shopkeeper manual sales (no real farmer)
INSERT IGNORE INTO users (email, password_hash, role, name, phone) VALUES
('walkin@agromart.local', '$2b$12$b7mVqjhDGbgKFEtRxcmeq.gLDIygGtyCRLwy2boSx4YmR/jN9xf1i', 'farmer', 'Walk-in Customer', '');
