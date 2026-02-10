import yfinance as yf

def get_market_data():
    tickers = {
        "SENSEX": "^BSESN",
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "NASDAQ 100": "^NDX"
    }
    
    data = {}
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # fast_info is faster than history
            price = ticker.fast_info['lastPrice']
            prev_close = ticker.fast_info['previousClose']
            change = price - prev_close
            change_percent = (change / prev_close) * 100
            
            data[name] = {
                "price": round(price, 2),
                "change": round(change_percent, 2),
                "symbol": symbol
            }
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            data[name] = {"price": 0, "change": 0}
            
    print(data)

if __name__ == "__main__":
    get_market_data()
