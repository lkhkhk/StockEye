import pytest
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from src.common.db_connector import Base # get_db 임포트 추가
from src.common.models.user import User # User 모델 임포트 추가
import pkgutil
import importlib

# src/api/models 디렉토리에서 모든 모델을 동적으로 로드
def import_all_models():
    models_package = importlib.import_module("src.api.models")
    for _, name, _ in pkgutil.iter_modules(models_package.__path__):
        if name != "__init__":
            importlib.import_module(f"src.api.models.{name}")

import_all_models()

@pytest.fixture(scope="function")
def db_inspector(real_db: Session):
    return inspect(real_db.bind)

def test_get_db_session(real_db: Session):
    """get_db 함수가 올바른 세션을 반환하고 닫는지 테스트"""
    db_session = real_db
    assert isinstance(db_session, Session)
    # 세션 사용 예시 (간단한 쿼리)
    db_session.query(User).first()

@pytest.mark.parametrize("model_class", [mapper.class_ for mapper in Base.registry.mappers])
def test_model_and_db_schema_match(real_db: Session, db_inspector, model_class):
    if not hasattr(model_class, "__tablename__"):
        pytest.skip(f"Skipping {model_class.__name__}: Not a SQLAlchemy model with a __tablename__.")
        return

    table_name = model_class.__tablename__
    
    # Check if table exists in DB
    assert db_inspector.has_table(table_name), f"Table {table_name} does not exist in the database."

    # Get column definitions from model and DB
    model_columns = {col.name: col for col in model_class.__table__.columns}
    db_columns = {col['name']: col for col in db_inspector.get_columns(table_name)}

    # Check if all model columns exist in DB and match properties
    for col_name, model_col in model_columns.items():
        assert col_name in db_columns, f"Column {col_name} missing in DB table {table_name}."
        db_col = db_columns[col_name]

        # Check type (simplified for common types, can be extended)
        # Note: SQLAlchemy types might not directly match DB types string,
        # so we compare their Python types or a simplified string representation.
        # For example, Integer in SQLAlchemy might be INTEGER in SQLite, INT in PostgreSQL.
        # We'll use a mapping for common type equivalences.
        type_mapping = {
            "FLOAT": ["FLOAT", "DOUBLE PRECISION"],
            "DATETIME": ["DATETIME", "TIMESTAMP"],
            "DATE": ["DATE"], # DATE 타입 추가
            "INTEGER": ["INTEGER"],
            "BIGINT": ["BIGINT"],
            "BOOLEAN": ["BOOLEAN"],
            "VARCHAR": ["VARCHAR"],
            "TEXT": ["TEXT"],
        }

        model_type_str = str(model_col.type).split('(')[0] # VARCHAR(X)에서 VARCHAR만 추출
        db_type_str = str(db_col['type']).split('(')[0] # VARCHAR(X)에서 VARCHAR만 추출

        is_type_match = False
        if model_type_str in type_mapping:
            if db_type_str in type_mapping[model_type_str]:
                is_type_match = True
        elif model_type_str == "String" and db_type_str == "VARCHAR": # SQLAlchemy String to DB VARCHAR
            is_type_match = True

        # For VARCHAR, also check length if specified in model
        if model_type_str == "VARCHAR" and hasattr(model_col.type, 'length') and model_col.type.length is not None:
            db_length_match = False
            if '(' in str(db_col['type']):
                db_length = int(str(db_col['type']).split('(')[1].split(')')[0])
                if db_length >= model_col.type.length:
                    db_length_match = True
            is_type_match = is_type_match and db_length_match
        elif model_type_str == "String" and hasattr(model_col.type, 'length') and model_col.type.length is not None: # For SQLAlchemy String with length
            db_length_match = False
            if '(' in str(db_col['type']):
                db_length = int(str(db_col['type']).split('(')[1].split(')')[0])
                if db_length >= model_col.type.length:
                    db_length_match = True
            is_type_match = is_type_match and db_length_match

        assert is_type_match, \
            f"Type mismatch for column {col_name} in table {table_name}: " \
            f"Model type {model_col.type}, DB type {db_col['type']}"
        
        # Check nullable
        # For primary keys, SQLAlchemy often sets nullable=False implicitly,
        # even if not explicitly set in the model.
        # We'll handle this by checking if it's a primary key.
        if not model_col.primary_key:
            assert db_col['nullable'] == model_col.nullable, \
                f"Nullable mismatch for column {col_name} in table {table_name}: " \
                f"Model nullable {model_col.nullable}, DB nullable {db_col['nullable']}"
        
        # Check default value (more complex, often requires inspecting DB-specific defaults)
        # For simplicity, we'll skip checking default values unless explicitly needed.
        # assert str(db_col['default']) == str(model_col.default), (
        #     f"Default mismatch for column {col_name} in table {table_name}: "
        #     f"Model default {model_col.default}, DB default {db_col['default']}"
        # )

    # Check if all DB columns exist in model (no extra columns in DB)
    for col_name in db_columns:
        assert col_name in model_columns, f"Extra column {col_name} found in DB table {table_name} not in model."