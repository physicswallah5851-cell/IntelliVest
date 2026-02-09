from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    user = User.query.filter_by(email='demo@example.com').first()
    if user:
        user.password = generate_password_hash('password123', method='pbkdf2:sha256')
        db.session.commit()
        print(f"Password for {user.email} reset to 'password123'")
    else:
        print("User demo@example.com not found. Creating new user.")
        new_user = User(
            email='demo@example.com', 
            name='Demo User', 
            password=generate_password_hash('password123', method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()
        print("Created new user demo@example.com with password 'password123'")
