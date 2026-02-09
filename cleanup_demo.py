from app import app, db, User, Transaction, Budget

def delete_user_safely(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User {email} not found.")
            return

        print(f"Found user: {user.name} ({user.email})")
        
        # Delete related data first (Cascade delete manual implementation)
        # 1. Transactions
        tx_count = Transaction.query.filter_by(user_id=user.id).delete()
        print(f"Deleted {tx_count} transactions.")

        # 2. Budgets
        budget_count = Budget.query.filter_by(user_id=user.id).delete()
        print(f"Deleted {budget_count} budgets.")

        # 3. User
        db.session.delete(user)
        db.session.commit()
        print(f"Successfully deleted user {email} and all associated data.")

if __name__ == "__main__":
    delete_user_safely('demo@example.com')
