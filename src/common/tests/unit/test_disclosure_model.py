import pytest
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, BigInteger, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

# Define a new Base for testing purposes
TestBase = declarative_base()

class TestDisclosure(TestBase):
    __tablename__ = 'disclosures'
    id = Column(Integer, primary_key=True, autoincrement=True) # Use Integer for SQLite test
    stock_code = Column(String(20), nullable=False, index=True)
    corp_code = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    rcept_no = Column(String(20), nullable=False, unique=True)
    disclosed_at = Column(DateTime, nullable=False, index=True)
    url = Column(String(300), nullable=False)
    disclosure_type = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

# Setup in-memory SQLite database for testing
@pytest.fixture(scope='function')
def db_session():
    engine = create_engine('sqlite:///:memory:')
    TestBase.metadata.create_all(engine) # Use TestBase
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    TestBase.metadata.drop_all(engine)

def test_disclosure_table_name():
    assert TestDisclosure.__tablename__ == 'disclosures'

def test_disclosure_columns():
    columns = TestDisclosure.__table__.columns
    assert 'id' in columns
    assert isinstance(columns['id'], Column)
    assert columns['id'].type.python_type == int
    assert columns['id'].primary_key
    assert columns['id'].autoincrement

    assert 'stock_code' in columns
    assert isinstance(columns['stock_code'], Column)
    assert columns['stock_code'].type.python_type == str
    assert not columns['stock_code'].nullable
    assert columns['stock_code'].index

    assert 'corp_code' in columns
    assert isinstance(columns['corp_code'], Column)
    assert columns['corp_code'].type.python_type == str
    assert not columns['corp_code'].nullable
    assert columns['corp_code'].index

    assert 'title' in columns
    assert isinstance(columns['title'], Column)
    assert columns['title'].type.python_type == str
    assert not columns['title'].nullable

    assert 'rcept_no' in columns
    assert isinstance(columns['rcept_no'], Column)
    assert columns['rcept_no'].type.python_type == str
    assert not columns['rcept_no'].nullable
    assert columns['rcept_no'].unique

    assert 'disclosed_at' in columns
    assert isinstance(columns['disclosed_at'], Column)
    assert columns['disclosed_at'].type.python_type == datetime
    assert not columns['disclosed_at'].nullable
    assert columns['disclosed_at'].index

    assert 'url' in columns
    assert isinstance(columns['url'], Column)
    assert columns['url'].type.python_type == str
    assert not columns['url'].nullable

    assert 'disclosure_type' in columns
    assert isinstance(columns['disclosure_type'], Column)
    assert columns['disclosure_type'].type.python_type == str
    assert columns['disclosure_type'].nullable

    assert 'created_at' in columns
    assert isinstance(columns['created_at'], Column)
    assert columns['created_at'].type.python_type == datetime
    assert not columns['created_at'].nullable

    assert 'updated_at' in columns
    assert isinstance(columns['updated_at'], Column)
    assert columns['updated_at'].type.python_type == datetime
    assert not columns['updated_at'].nullable

def test_disclosure_instance_creation(db_session):
    disclosure = TestDisclosure(
        id=None, # Explicitly set to None for autoincrement
        stock_code='005930',
        corp_code='0012345',
        title='삼성전자 사업보고서',
        rcept_no='20230101000001',
        disclosed_at=datetime(2023, 1, 1, 10, 0, 0),
        url='http://example.com/disclosure/1',
        disclosure_type='사업보고서'
    )
    db_session.add(disclosure)
    db_session.commit()

    retrieved_disclosure = db_session.query(TestDisclosure).filter_by(rcept_no='20230101000001').first()
    assert retrieved_disclosure is not None
    assert retrieved_disclosure.stock_code == '005930'
    assert retrieved_disclosure.corp_code == '0012345'
    assert retrieved_disclosure.title == '삼성전자 사업보고서'
    assert retrieved_disclosure.rcept_no == '20230101000001'
    assert retrieved_disclosure.disclosed_at == datetime(2023, 1, 1, 10, 0, 0)
    assert retrieved_disclosure.url == 'http://example.com/disclosure/1'
    assert retrieved_disclosure.disclosure_type == '사업보고서'
    assert isinstance(retrieved_disclosure.created_at, datetime)
    assert isinstance(retrieved_disclosure.updated_at, datetime)
    assert retrieved_disclosure.created_at <= datetime.now()
    assert retrieved_disclosure.updated_at <= datetime.now()

def test_disclosure_updated_at_on_update(db_session):
    disclosure = TestDisclosure(
        id=None, # Explicitly set to None for autoincrement
        stock_code='005930',
        corp_code='0012345',
        title='삼성전자 사업보고서',
        rcept_no='20230101000002',
        disclosed_at=datetime(2023, 1, 1, 10, 0, 0),
        url='http://example.com/disclosure/2',
        disclosure_type='사업보고서'
    )
    db_session.add(disclosure)
    db_session.commit()
    
    original_updated_at = disclosure.updated_at
    
    # Update the disclosure
    disclosure.title = '삼성전자 정정보고서'
    db_session.add(disclosure)
    db_session.commit()
    
    # Retrieve the updated disclosure
    updated_disclosure = db_session.query(TestDisclosure).filter_by(rcept_no='20230101000002').first()
    
    assert updated_disclosure.title == '삼성전자 정정보고서'
    assert updated_disclosure.updated_at > original_updated_at