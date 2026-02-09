from app import app, db, User
from werkzeug.security import check_password_hash

with app.app_context():
    user = User.query.filter_by(email='demo@example.com').first()
    if user:
        print(f"User found: {user.name}")
        print(f"Password hash: {user.password}")
        is_valid = check_password_hash(user.password, 'password123')
        print(f"Password 'password123' valid? {is_valid}")
    else:
        print("User demo@example.com not found")
