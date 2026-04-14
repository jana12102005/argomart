-- Default admin (shopkeeper) for AgroHands AI
-- Run this in phpMyAdmin (select database agromart) → Import or SQL tab
-- Password: admin123

USE agromart;

INSERT INTO users (email, password_hash, role, name, phone) VALUES
('admin@agromart.com', '$2b$12$b7mVqjhDGbgKFEtRxcmeq.gLDIygGtyCRLwy2boSx4YmR/jN9xf1i', 'shopkeeper', 'Admin', '');

SET @admin_id = LAST_INSERT_ID();

INSERT INTO shops (owner_id, name, address, phone) VALUES
(@admin_id, 'Admin Shop', '', '');

-- Walk-in customer for manual sales (no real farmer)
INSERT IGNORE INTO users (email, password_hash, role, name, phone) VALUES
('walkin@agromart.local', '$2b$12$b7mVqjhDGbgKFEtRxcmeq.gLDIygGtyCRLwy2boSx4YmR/jN9xf1i', 'farmer', 'Walk-in Customer', '');
