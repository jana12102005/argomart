# Auth helpers: password hashing, user load from DB
import bcrypt
from flask_login import UserMixin
from db import get_connection

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

class User(UserMixin):
    def __init__(self, id, email, role, name, phone, shop_id=None):
        self.id = id
        self.email = email
        self.role = role
        self.name = name
        self.phone = phone
        self.shop_id = shop_id

    @staticmethod
    def get(user_id):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id, email, role, name, phone FROM users WHERE id = %s',
                    (user_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=row['id'],
                    email=row['email'],
                    role=row['role'],
                    name=row['name'],
                    phone=row.get('phone') or '',
                    shop_id=None,
                )
        finally:
            conn.close()

    def get_shop_id(self):
        """For shopkeeper: get shop id (from shops table by owner_id)."""
        if self.shop_id:
            return self.shop_id
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM shops WHERE owner_id = %s', (self.id,))
                row = cur.fetchone()
                return row['id'] if row else None
        finally:
            conn.close()
