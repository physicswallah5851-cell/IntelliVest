from flask import Blueprint, request, session, redirect, url_for, flash, render_template, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Transaction, Budget
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

def seed_data(user_id):
    # Add some dummy transactions
    t1 = Transaction(user_id=user_id, description="Opening Balance", amount=50000.00, category="Income", date=datetime.now())
    t2 = Transaction(user_id=user_id, description="Netflix", amount=-650.00, category="Entertainment", date=datetime.now())
    db.session.add_all([t1, t2])
    
    # Add dummy budgets
    b1 = Budget(user_id=user_id, name="Groceries", limit=15000, spent=8000, icon="fas fa-shopping-basket", color="#10B981")
    b2 = Budget(user_id=user_id, name="Entertainment", limit=5000, spent=1200, icon="fas fa-film", color="#8B5CF6")
    b3 = Budget(user_id=user_id, name="Dining Out", limit=8000, spent=4500, icon="fas fa-utensils", color="#EF4444")
    db.session.add_all([b1, b2, b3])
    
    db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.password, password):
                login_user(user)
                session['name'] = user.name
                session['initials'] = ''.join([n[0] for n in user.name.split()[:2]]).upper()
                return redirect(url_for('views.home'))
            else:
                flash('Invalid email or password', 'error')
        except Exception as e:
            current_app.logger.error(f"Login Error: {e}")
            flash(f"Login Error: {str(e)}", 'error')
            
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Email already exists', 'error')
                return redirect(url_for('auth.signup'))
                
            new_user = User(
                email=email, 
                name=name, 
                password=generate_password_hash(password, method='pbkdf2:sha256')
            )
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user)
            session['name'] = new_user.name
            session['initials'] = ''.join([n[0] for n in new_user.name.split()[:2]]).upper()
            
            seed_data(new_user.id)
            
            return redirect(url_for('views.home'))
        except Exception as e:
            current_app.logger.error(f"Signup Error: {e}")
            flash(f"Signup failed: {str(e)}", 'error')
            return redirect(url_for('auth.signup'))
            
    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))
