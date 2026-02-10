from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import yfinance as yf
from models import db, User, Transaction, Portfolio, Budget

app = Flask(__name__)
# Changed key to invalidate old sessions
app.secret_key = 'intellivest_secure_v3_key_reset_final'

import os
basedir = os.path.abspath(os.path.dirname(__file__))

# Priority: Environment variable (Render PostgreSQL), Fallback: Local SQLite
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or ('sqlite:///' + os.path.join(basedir, 'finance_v2.db'))
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
    current_savings = current_user.initial_balance + income - expenses
    
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
            "data": [current_user.initial_balance, current_user.initial_balance * 1.1, current_user.initial_balance * 1.05, current_user.initial_balance * 1.2, current_user.initial_balance * 1.15, current_savings]
        }
    })

@app.route('/api/user/balance', methods=['POST'])
@login_required
def update_initial_balance():
    data = request.get_json(silent=True) or {}
    try:
        current_user.initial_balance = float(data.get('balance', 100000.0))
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/transactions', methods=['POST'])
@login_required
def add_transaction():
    data = request.get_json(silent=True) or {}
    try:
        new_tx = Transaction(
            user_id=current_user.id,
            description=data.get('description', 'Untitled'),
            amount=float(data.get('amount', 0)),
            category=data.get('category', 'General'),
            date=datetime.now()
        )
        db.session.add(new_tx)
        db.session.commit()
        return jsonify({"status": "success", "message": "Transaction added"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/transactions/<int:tx_id>', methods=['DELETE'])
@login_required
def delete_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if tx:
        db.session.delete(tx)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404
@app.route('/api/simulation', methods=['POST'])
@login_required
def simulation_api():
    data = request.get_json(silent=True) or {}
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
    return jsonify([{
        "id": b.id,
        "name": b.name,
        "limit": b.limit,
        "spent": b.spent,
        "icon": b.icon,
        "color": b.color,
        "transactions": Transaction.query.filter_by(user_id=current_user.id, category=b.name).count()
    } for b in current_user.budgets])

@app.route('/api/budgets', methods=['POST'])
@login_required
def save_budget():
    data = request.get_json(silent=True) or {}
    try:
        budget_id = data.get('id')
        if budget_id:
            budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
        else:
            budget = Budget(user_id=current_user.id)
            db.session.add(budget)
            
        budget.name = data.get('name', 'New Category')
        budget.limit = float(data.get('limit', 0))
        budget.icon = data.get('icon', 'fas fa-wallet')
        budget.color = data.get('color', '#3B82F6')
        
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if budget:
        db.session.delete(budget)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404

@app.route('/api/portfolio')
@login_required
def portfolio_api():
    plans = Portfolio.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "id": p.id,
        "symbol": p.symbol,
        "company_name": p.company_name,
        "date": p.added_at.strftime('%Y-%m-%d')
    } for p in plans])

@app.route('/api/portfolio', methods=['POST'])
@login_required
def save_portfolio():
    data = request.get_json(silent=True) or {}
    try:
        new_plan = Portfolio(
            user_id=current_user.id,
            symbol=data.get('symbol'),
            company_name=data.get('company_name')
        )
        db.session.add(new_plan)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/portfolio/<int:plan_id>', methods=['DELETE'])
@login_required
def delete_portfolio(plan_id):
    plan = Portfolio.query.filter_by(id=plan_id, user_id=current_user.id).first()
    if plan:
        db.session.delete(plan)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404

# --- Market Data APIs ---
@app.route('/api/market/indices')
def get_market_indices():
    # SENSEX (^BSESN), NIFTY 50 (^NSEI), BANK NIFTY (^NSEBANK), NASDAQ (^IXIC)
    tickers = {
        "SENSEX": "^BSESN",
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "NASDAQ": "^IXIC"
    }
    
    data = []
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # Use fast_info for better performance
            price = ticker.fast_info.last_price
            prev = ticker.fast_info.previous_close
            change = price - prev
            change_p = (change / prev) * 100
            
            data.append({
                "name": name,
                "price": round(price, 2),
                "change": round(change_p, 2),
                "symbol": symbol
            })
        except:
            # Fallback if API fails
            data.append({
                "name": name,
                "price": 0,
                "change": 0,
                "symbol": symbol
            })
            
    return jsonify(data)

@app.route('/api/market/stocks', methods=['POST'])
def get_stock_prices():
    # Expects a list of symbols e.g. ["RELIANCE.NS", "TCS.NS"]
    req = request.get_json(silent=True) or {}
    symbols = req.get('symbols', [])
    
    if not symbols:
        return jsonify([])
        
    data = []
    for sym in symbols:
        try:
            # Append .NS if not present for Indian stocks (rudimentary check)
            lookup_sym = sym if ('.' in sym or '^' in sym) else f"{sym}.NS"
            
            ticker = yf.Ticker(lookup_sym)
            price = ticker.fast_info.last_price
            prev = ticker.fast_info.previous_close
            change = (price - prev) / prev * 100
            
            data.append({
                "symbol": sym, # Return original symbol requested
                "price": round(price, 2),
                "change": round(change, 2)
            })
        except:
            pass
            
    return jsonify(data)


# --- Routes ---
@app.route('/api/market/history/<path:symbol>')
@login_required
def get_stock_history(symbol):
    try:
        # Fetch max history
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max")
        
        # Data reduction: If too many points, resample
        # Take every Nth point to keep JSON size manageable (~500 points max)
        total_points = len(hist)
        step = max(1, total_points // 500)
        
        subset = hist.iloc[::step]
        
        chart_data = {
            "labels": subset.index.strftime('%Y-%m-%d').tolist(),
            "data": subset['Close'].round(2).tolist()
        }
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
    # Dynamically get the current host (works for both Local and Render)
    public_url = request.host_url.rstrip('/')
    return render_template('mobile.html', url=public_url)

@app.route('/debug')
def debug_info():
    try:
        import os
        cwd = os.getcwd()
        writable = os.access(cwd, os.W_OK)
        db_path = app.config['SQLALCHEMY_DATABASE_URI']
        
        # Try DB connection
        user_count = -1
        try:
            user_count = User.query.count()
            db_status = "Connected"
        except Exception as e:
            db_status = f"Error: {e}"
            
        return jsonify({
            "cwd": cwd,
            "writable": writable,
            "db_path": db_path,
            "db_status": db_status,
            "user_count": user_count
        })
    except Exception as e:
        return str(e)


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
