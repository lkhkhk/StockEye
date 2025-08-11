from sqlalchemy.orm import Session
from src.common.db_connector import SessionLocal
from src.api.models.stock_master import StockMaster

def check_db_data():
    db: Session = SessionLocal()
    try:
        stocks = db.query(StockMaster).all()
        if not stocks:
            print("StockMaster 테이블에 데이터가 없습니다.")
        else:
            print(f"StockMaster 테이블 데이터 ({len(stocks)}개):")
            for stock in stocks:
                print(f"- Symbol: {stock.symbol}, Name: {stock.name}, Market: {stock.market}")
    except Exception as e:
        print(f"DB 조회 중 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db_data()
