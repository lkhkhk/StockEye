import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time

DATABASE_URL = "stock_prediction.db"

def get_db():
    db = sqlite3.connect(DATABASE_URL)
    db.row_factory = sqlite3.Row
    return db

def init_db_data():
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL, -- YYYY-MM-DD
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (symbol, date)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL, -- YYYY-MM-DD
                indicator_name TEXT NOT NULL,
                value REAL,
                PRIMARY KEY (symbol, date, indicator_name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                symbol TEXT NOT NULL,
                date TEXT NOT NULL, -- YYYY-MM-DD
                title TEXT NOT NULL,
                url TEXT,
                summary TEXT,
                PRIMARY KEY (symbol, date, title) -- Assuming title is unique enough for a given day/symbol
            )
        """)
        db.commit()

def fetch_stock_data(symbol):
    """
    네이버 금융에서 특정 종목의 주가 데이터를 크롤링합니다.
    TODO: 실제 크롤링 로직 구현 (페이지 파싱, 여러 페이지 처리 등)
    현재는 placeholder 데이터 반환
    """
    print(f"Fetching data for {symbol}...")
    # Example URL structure (may need adjustment based on actual Naver Finance structure)
    # url = f"https://finance.naver.com/item/sise_day.naver?code={symbol}"
    # try:
    #     response = requests.get(url)
    #     response.raise_for_status() # Raise an exception for bad status codes
    #     soup = BeautifulSoup(response.content, 'html.parser')
    #     # TODO: Parse soup to extract data
    #     print(f"Data fetched for {symbol}")
    #     return [{"date": "2023-01-01", "open": 10000, "high": 10500, "low": 9800, "close": 10300, "volume": 100000}] # Placeholder
    # except requests.exceptions.RequestException as e:
    #     print(f"Error fetching data for {symbol}: {e}")
    #     return None
    # except Exception as e:
    #     print(f"Error parsing data for {symbol}: {e}")
    #     return None

    url = f"https://finance.naver.com/item/sise_day.naver?code={symbol}&page=5"
    url = f"https://finance.naver.com/item/sise_day.naver?code={symbol}"
    data_list = []
    try:
        print(f"Fetching data for {symbol} from {url}...")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}) # Add User-Agent header
        response.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the table containing daily prices (assuming it's the first table or has a specific class/id)
        # This part might need adjustment based on actual Naver Finance HTML structure
        table = soup.find("table", class_="type2") # Example: find table with class "type2"
        if table:
            rows = table.select("tr")
            # Iterate through rows, skipping header and footer if present
            for row in rows[1:]: # Skip header row
                cols = row.select("td")
                if len(cols) > 6: # Ensure enough columns exist (Date, Close, Change, Open, High, Low, Volume)
                    try:
                        # Extract data - column indices might need adjustment
                        date_str = cols[0].get_text().strip()
                        # Skip rows that are just separators or empty
                        if not date_str or date_str.startswith('날짜'):
                            continue

                        date_obj = datetime.strptime(date_str, "%Y.%m.%d").strftime("%Y-%m-%d")
                        close_price = int(cols[1].get_text().strip().replace(',', ''))
                        open_price = int(cols[3].get_text().strip().replace(',', ''))
                        high_price = int(cols[4].get_text().strip().replace(',', ''))
                        low_price = int(cols[5].get_text().strip().replace(',', ''))
                        volume = int(cols[6].get_text().strip().replace(',', ''))

                        data_list.append({
                            "date": date_obj,
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": volume
                        })
                        # For this basic implementation, we only process the first page's data
                        # To handle multiple pages, you would need to find pagination links and loop through them.
                    except ValueError as ve:
                        print(f"Could not parse data in row: {ve}")
                    except Exception as ex:
                        print(f"Error processing row: {ex}")

        print(f"Data fetched for {symbol}. Found {len(data_list)} entries.")
        return data_list

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing data for {symbol}: {e}")
        return None


def store_stock_data(symbol, data):
    """
    수집된 주가 데이터를 데이터베이스에 저장합니다.
    """
    if not data:
        print(f"No data to store for {symbol}")
        return

    with get_db() as db:
        cursor = db.cursor()
        for entry in data:
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO daily_prices (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, entry["date"], entry["open"], entry["high"], entry["low"], entry["close"], entry["volume"])
                )
                print(f"Stored data for {symbol} on {entry['date']}")
            except Exception as e:
                print(f"Error storing data for {symbol} on {entry['date']}: {e}")
        db.commit()

def collect_all_stock_data():
    """
    모든 관심 종목 또는 전체 종목에 대한 데이터를 수집합니다.
    TODO: 전체 종목 목록 가져오는 로직 추가
    """
    # For now, collect data for a few example symbols
#    symbols_to_collect = ["005930", "035720", "000660"] # 삼성전자, 카카오, SK하이닉스
    symbols_to_collect = ["005930", "035720", "000660", "042660", "064350"] # 삼성전자, 카카오, SK하이닉스, 한화오션, 현대로템
    print("Starting data collection...")
    init_db_data() # Ensure data table exists

    for symbol in symbols_to_collect:
        data = fetch_stock_data(symbol)
        if data:
            store_stock_data(symbol, data)
        # Add a small delay to avoid overwhelming the source server
        time.sleep(1)
    print("Data collection finished.")

if __name__ == "__main__":
    # Example usage: Run data collection when the script is executed directly
    collect_all_stock_data()
