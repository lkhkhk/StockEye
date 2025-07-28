import pytest
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from src.common.db_connector import Base
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
def db_inspector(db: Session):
    return inspect(db.bind)

@pytest.mark.parametrize("model_class", [mapper.class_ for mapper in Base.registry.mappers])
def test_model_and_db_schema_match(db: Session, db_inspector, model_class):
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
        # We'll compare the Python type of the SQLAlchemy column type.
        assert isinstance(db_col['type'], type(model_col.type)), \
            f"Type mismatch for column {col_name} in table {table_name}: " \
            f"Model type {type(model_col.type).__name__}, DB type {type(db_col['type']).__name__}"
        
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