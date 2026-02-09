from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Transaction, Portfolio, Budget

app = Flask(__name__)
# Changed key to invalidate old sessions
app.secret_key = 'intellivest_secure_v3_key_reset_final'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- API Endpoints ---
@app.route('/api/dashboard')
@login_required
def dashboard_api():
    # Fetch Real Data
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    
    # Calculate Totals
    income = sum(t.amount for t in transactions if t.amount > 0)
    expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
    current_savings = 100000 + income - expenses # Starting base + delta
    
    # Format Transactions
    tx_list = []
    for t in transactions[:5]: # Last 5
        tx_list.append({
            "id": t.id,
            "desc": t.description,
            "amt": t.amount,
            "date": t.date.strftime('%Y-%m-%d'),
            "cat": t.category
        })
        
    return jsonify({
        "balance": current_savings,
        "income": income,
        "expenses": expenses,
        "transactions": tx_list,
        "chart": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "data": [100000, 110000, 105000, 120000, 115000, current_savings]
        }
    })
@app.route('/api/simulation', methods=['POST'])
@login_required
def simulation_api():
    data = request.get_json()
    cost = float(data.get('cost', 0))
    monthly = float(data.get('monthly', 0))
    
    # Logic: 
    # Current Path: Just saving the monthly amount + cost (0% interest)
    # New Scenario: Investing monthly at 12% p.a + cost invested
    
    years = 10
    labels = [f"Year {i}" for i in range(1, years + 1)]
    base_trend = []
    sim_trend = []
    
    current_base = cost
    current_sim = cost
    
    for _ in range(years):
        # Base: Simple accumulation
        current_base += (monthly * 12)
        base_trend.append(round(current_base))
        
        # Sim: Compound Interest (12% p.a)
        # SV = P * (1+r/n)^(nt) ... simplified for yearly step
        investment = monthly * 12
        current_sim = (current_sim + investment) * 1.12
        sim_trend.append(round(current_sim))
    
    # Advice logic
    diff = sim_trend[-1] - base_trend[-1]
    advice = f"By investing ₹{int(monthly):,} monthly instead of just saving, you could create an additional wealth of ₹{int(diff):,} in 10 years. That's the power of compounding!"
    
    return jsonify({
        "labels": labels,
        "base_trend": base_trend,
        "sim_trend": sim_trend,
        "status": "safe" if monthly > 0 else "risk",
        "advice": advice
    })

@app.route('/api/budgets')
@login_required
def budgets_api():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "limit": b.limit,
        "spent": b.spent,
        "icon": b.icon,
        "color": b.color,
        "transactions": 12 # Mock count for now, or link to real tx count later
    } for b in budgets])

# --- Routes ---
@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            # Session info for templates - DYNAMIC now
            session['name'] = user.name
            session['initials'] = ''.join([n[0] for n in user.name.split()[:2]]).upper()
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            
            # Helper to check if user exists
            user = User.query.filter_by(email=email).first()
            if user:
                flash('Email already exists', 'error')
                return redirect(url_for('signup'))
                
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
            
            # Seed initial data for new user
            seed_data(new_user.id)
            
            return redirect(url_for('home'))
        except Exception as e:
            app.logger.error(f"Signup Error: {e}")
            flash(f"Signup failed: {str(e)}", 'error')
            return redirect(url_for('signup'))
            
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/market')
@login_required
def market():
    return render_template('market.html')

@app.route('/invest')
@login_required
def invest():
    return render_template('invest.html')

@app.route('/budgets')
@login_required
def budgets():
    return render_template('budgets.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/calculator')
@login_required
def calculator():
    return render_template('calculator.html')

@app.route('/mobile')
def mobile_access():
    # Hardcoded public URL from the active tunnel
    public_url = "https://684c73edcce0a428-115-245-68-163.serveousercontent.com"
    return render_template('mobile.html', url=public_url)


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
    
# Create DB if not exists (This runs on Import for Gunicorn)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
        
    # Run on all interfaces for tunnel compatibility
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
