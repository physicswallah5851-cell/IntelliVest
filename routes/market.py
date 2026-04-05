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
@cache.cached(timeout=600)  # Cache for 10 minutes
def get_market_news():
    import re
    import email.utils

    # Indian financial news RSS feeds — fast, reliable, updated throughout the trading day
    feeds = [
        {
            "url": "https://economictimes.indiatimes.com/markets/rss.cms",
            "source": "Economic Times",
            "type": "Markets",
            "color": "blue"
        },
        {
            "url": "https://www.moneycontrol.com/rss/MCtopnews.xml",
            "source": "MoneyControl",
            "type": "Top News",
            "color": "green"
        },
        {
            "url": "https://feeds.feedburner.com/ndtvnews-business",
            "source": "NDTV Business",
            "type": "Business",
            "color": "red"
        },
        {
            "url": "https://www.livemint.com/rss/markets",
            "source": "LiveMint",
            "type": "Markets",
            "color": "purple"
        }
    ]

    # Spoof a browser User-Agent to prevent 403 Forbidden responses from feed servers
    ua_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    news_items = []

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"], request_headers=ua_headers)

            if parsed.bozo and not parsed.entries:
                print(f"Feed bozo error for {feed['source']}: {parsed.bozo_exception}")
                continue

            for entry in parsed.entries[:6]:
                summary = ""
                if hasattr(entry, 'summary'):
                    summary = re.sub(r'<[^>]+>', '', entry.summary).strip()
                    if len(summary) > 180:
                        summary = summary[:177] + "..."
                elif hasattr(entry, 'description'):
                    summary = re.sub(r'<[^>]+>', '', entry.description).strip()
                    if len(summary) > 180:
                        summary = summary[:177] + "..."

                # Skip entries with no real content
                if not entry.get('title', '').strip():
                    continue

                news_items.append({
                    "title": entry.title.strip(),
                    "link": entry.get('link', '#'),
                    "published": entry.get('published', entry.get('updated', '')),
                    "source": feed["source"],
                    "type": feed["type"],
                    "color": feed["color"],
                    "summary": summary
                })
        except Exception as e:
            print(f"Error parsing feed {feed['source']} ({feed['url']}): {e}")
            # Continue processing remaining feeds even if one fails
            continue

    def parse_pub_date(date_str):
        if not date_str:
            return 0
        try:
            parsed_date = email.utils.parsedate_tz(date_str)
            if parsed_date:
                return email.utils.mktime_tz(parsed_date)
            return 0
        except Exception:
            return 0

    # Sort newest first across all feeds
    news_items.sort(key=lambda x: parse_pub_date(x['published']), reverse=True)

    return jsonify(news_items[:16])  # Return top 16 combined
