
import datetime
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestModel(Base):
    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    test_date = Column(String) # Store as string

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Store a datetime object
dt_obj = datetime.datetime.now()
test_instance = TestModel(test_date=dt_obj.isoformat())
session.add(test_instance)
session.commit()

# Retrieve the string
retrieved_string = session.query(TestModel).first().test_date
print(f"Retrieved string: {retrieved_string}")

# Try to parse it
try:
    parsed_dt = datetime.datetime.fromisoformat(retrieved_string)
    print(f"Parsed datetime: {parsed_dt}")
except ValueError as e:
    print(f"ValueError: {e}")

session.close()
