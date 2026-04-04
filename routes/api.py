import os
import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Transaction, Budget, Portfolio
from datetime import datetime

import time
import random
api_bp = Blueprint('api', __name__)

@api_bp.route('/dashboard')
@login_required
def dashboard_api():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    
    income = sum(t.amount for t in transactions if t.amount > 0)
    expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
    current_savings = current_user.initial_balance + income - expenses
    
    tx_list = []
    for t in transactions[:5]:
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

@api_bp.route('/user/balance', methods=['POST'])
@login_required
def update_initial_balance():
    data = request.get_json(silent=True) or {}
    try:
        current_user.initial_balance = float(data.get('balance', 100000.0))
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": "Invalid balance format"}), 400

@api_bp.route('/transactions', methods=['POST'])
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
        return jsonify({"status": "error", "message": "Invalid transaction data"}), 400

@api_bp.route('/transactions/<int:tx_id>', methods=['DELETE'])
@login_required
def delete_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if tx:
        db.session.delete(tx)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404

@api_bp.route('/simulation', methods=['POST'])
@login_required
def simulation_api():
    data = request.get_json(silent=True) or {}
    cost = float(data.get('cost', 0))
    monthly = float(data.get('monthly', 0))
    
    years = 10
    labels = [f"Year {i}" for i in range(1, years + 1)]
    base_trend = []
    sim_trend = []
    
    current_base = cost
    current_sim = cost
    
    for _ in range(years):
        current_base += (monthly * 12)
        base_trend.append(round(current_base))
        
        investment = monthly * 12
        current_sim = (current_sim + investment) * 1.12
        sim_trend.append(round(current_sim))
    
    diff = sim_trend[-1] - base_trend[-1]
    advice = f"By investing ₹{int(monthly):,} monthly instead of just saving, you could create an additional wealth of ₹{int(diff):,} in 10 years. That's the power of compounding!"
    
    return jsonify({
        "labels": labels,
        "base_trend": base_trend,
        "sim_trend": sim_trend,
        "status": "safe" if monthly > 0 else "risk",
        "advice": advice
    })

@api_bp.route('/budgets')
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

@api_bp.route('/budgets', methods=['POST'])
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
        return jsonify({"status": "error", "message": "Invalid budget data"}), 400

@api_bp.route('/budgets/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if budget:
        db.session.delete(budget)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404

@api_bp.route('/portfolio')
@login_required
def portfolio_api():
    plans = Portfolio.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        "id": p.id,
        "symbol": p.symbol,
        "company_name": p.company_name,
        "date": p.added_at.strftime('%Y-%m-%d')
    } for p in plans])

@api_bp.route('/portfolio', methods=['POST'])
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
        return jsonify({"status": "error", "message": "Invalid portfolio data"}), 400

@api_bp.route('/portfolio/<int:plan_id>', methods=['DELETE'])
@login_required
def delete_portfolio(plan_id):
    plan = Portfolio.query.filter_by(id=plan_id, user_id=current_user.id).first()
    if plan:
        db.session.delete(plan)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404

@api_bp.route('/invest/ai', methods=['POST'])
@login_required
def invest_ai_api():
    data = request.get_json(silent=True) or {}
    amount = float(data.get('amount', 100000))
    risk = data.get('risk', 'medium')
    age = int(data.get('age', 30))
    occupation = data.get('occupation', 'Professional')
    goal = data.get('goal', 'Wealth Accumulation')
    
    # Synthetic delay to mimic computational processing
    time.sleep(1.5)

    stocks = crypto = real_estate = gold = fd = bonds = 0

    if risk == 'high':
        stocks = max(60, 110 - age)
        crypto = 10
        real_estate = max(10, 30 - int(age/2))
        remainder = max(0, 100 - stocks - crypto - real_estate)
        gold = int(remainder * 0.6)
        fd = remainder - gold
        reasoning = f"As a {age}-year-old {occupation} striving for {goal}, we are optimizing your portfolio for maximum capital appreciation. A heavy {stocks}% weighting in equities leverages the power of compounding, while a {crypto}% alternative exposure aims to generate outsized alpha."
    elif risk == 'medium':
        stocks = max(40, 100 - age)
        real_estate = 15
        gold = 15
        fd = 100 - stocks - real_estate - gold
        reasoning = f"Given your profession as a {occupation} and your age ({age}), {goal} requires a balanced approach. We allocate {stocks}% to growth-oriented stocks, while anchoring the remaining portfolio with {fd}% in fixed-income to securely hedge against market drawdowns."
    else:
        fd = max(50, age)
        bonds = 20
        gold = 20
        stocks = 100 - fd - bonds - gold
        if stocks < 0:
            fd += stocks; stocks = 0
        reasoning = f"Because your primary objective is {goal}, we have heavily defended this ₹{amount:,.0f} portfolio. As a {age}-year-old {occupation}, allocating {fd}% in government-backed Fixed Deposits and {bonds}% in stable sovereign bonds isolates you from severe market corrections."

    allocations = []
    if stocks > 0: allocations.append({"label": "Stocks", "percent": stocks, "color": "#8B5CF6", "growth": 1.12})
    if crypto > 0: allocations.append({"label": "Crypto/Alt", "percent": crypto, "color": "#EF4444", "growth": 1.25})
    if real_estate > 0: allocations.append({"label": "Real Estate", "percent": real_estate, "color": "#EC4899", "growth": 1.09})
    if gold > 0: allocations.append({"label": "Gold", "percent": gold, "color": "#F59E0B", "growth": 1.08})
    if fd > 0: allocations.append({"label": "Fixed Deposits (FD)", "percent": fd, "color": "#3B82F6", "growth": 1.07})
    if bonds > 0: allocations.append({"label": "Govt Bonds", "percent": bonds, "color": "#10B981", "growth": 1.06})

    return jsonify({
        "status": "success",
        "data": {
            "allocation": allocations,
            "reasoning": reasoning
        }
    })
