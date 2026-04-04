from flask import Blueprint, request, jsonify
from flask_login import login_required
import yfinance as yf
import feedparser
from extensions import cache

market_bp = Blueprint('market', __name__)

@market_bp.route('/indices')
@cache.cached(timeout=60) # Cache for 60 seconds to prevent rate limiting
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
            data.append({
                "name": name,
                "price": 0,
                "change": 0,
                "symbol": symbol
            })
            
    return jsonify(data)

@market_bp.route('/stocks', methods=['POST'])
def get_stock_prices():
    req = request.get_json(silent=True) or {}
    symbols = req.get('symbols', [])
    
    if not symbols:
        return jsonify([])
        
    data = []
    for sym in symbols:
        try:
            lookup_sym = sym if ('.' in sym or '^' in sym) else f"{sym}.NS"
            
            ticker = yf.Ticker(lookup_sym)
            price = ticker.fast_info.last_price
            prev = ticker.fast_info.previous_close
            change = (price - prev) / prev * 100
            
            data.append({
                "symbol": sym, 
                "price": round(price, 2),
                "change": round(change, 2)
            })
        except:
            pass
            
    return jsonify(data)

@market_bp.route('/history/<path:symbol>')
@login_required
@cache.cached(timeout=3600, key_prefix=lambda: f"hist_{request.path}") # Cache history for 1 hour
def get_stock_history(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max")
        
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

@market_bp.route('/news')
@cache.cached(timeout=900) # Cache for 15 minutes
def get_market_news():
    feeds = [
        {"url": "https://www.theguardian.com/business/rss", "source": "The Guardian", "type": "Business"},
        {"url": "https://www.economist.com/finance-and-economics/rss.xml", "source": "The Economist", "type": "Finance"}
    ]
    
    news_items = []
    
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:8]: 
                summary = ""
                if hasattr(entry, 'summary'):
                    # Strip basic HTML tags from summary for a clean preview text
                    import re
                    summary = re.sub('<[^<]+?>', '', entry.summary)
                    if len(summary) > 150: summary = summary[:147] + "..."
                    
                news_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get('published', ''),
                    "source": feed["source"],
                    "type": feed["type"],
                    "summary": summary
                })
        except Exception as e:
            print(f"Error parsing feed {feed['url']}: {e}")
            
    import email.utils
    def parse_pub_date(date_str):
        try:
            parsed_date = email.utils.parsedate_tz(date_str)
            if parsed_date:
                return email.utils.mktime_tz(parsed_date)
            return 0
        except:
            return 0

    # Sort so newest items across both feeds appear first
    news_items.sort(key=lambda x: parse_pub_date(x['published']), reverse=True)
    
    return jsonify(news_items[:12]) # Return top 12 combined
