from app import app, db, User

with app.app_context():
    users = User.query.all()
    if not users:
        print("No users found.")
    else:
        for u in users:
            print(f"Email: {u.email} | Name: {u.name}")
