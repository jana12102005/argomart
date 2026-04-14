-- Optional: allow walk-in sales (no farmer linked). Run in phpMyAdmin if you use Record Sale without a customer.
USE agromart;
ALTER TABLE transactions MODIFY farmer_id INT NULL;
