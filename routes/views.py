from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import User
from config import Config

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
@login_required
def home():
    return render_template('index.html')

@views_bp.route('/market')
@login_required
def market():
    return render_template('market.html')

@views_bp.route('/invest')
@login_required
def invest():
    return render_template('invest.html')

@views_bp.route('/budgets')
@login_required
def budgets():
    return render_template('budgets.html')

@views_bp.route('/academy')
@login_required
def academy():
    return render_template('academy.html')

@views_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@views_bp.route('/calculator')
@login_required
def calculator():
    return render_template('calculator.html')

@views_bp.route('/mobile')
def mobile_access():
    public_url = request.host_url.rstrip('/')
    return render_template('mobile.html', url=public_url)

@views_bp.route('/debug')
def debug_info():
    try:
        import os
        from models import db
        cwd = os.getcwd()
        writable = os.access(cwd, os.W_OK)
        # Assuming db_path is known or just showing safe info
        
        user_count = -1
        try:
            user_count = User.query.count()
            db_status = "Connected"
        except Exception as e:
            db_status = f"Error: {e}"
            
        return jsonify({
            "cwd": cwd,
            "writable": writable,
            "db_status": db_status,
            "user_count": user_count
        })
    except Exception as e:
        return str(e)
