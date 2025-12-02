# src/api/tests/integration/test_db_schema_integration.py
"""
**DB-모델 스키마 무결성 테스트**

이 파일은 API의 기능 테스트가 아닌, 프로젝트의 안정성을 위한 메타(meta) 테스트입니다.

**목적**:
- SQLAlchemy로 정의된 모델(`src/common/models`)과 실제 데이터베이스의 테이블 스키마가
  100% 일치하는지 검증합니다.
- 코드(모델)와 DB(스키마) 간의 불일치로 인해 발생할 수 있는 런타임 오류를 사전에 방지합니다.

**동작 방식**:
1. `src/common/models` 디렉토리 내의 모든 파이썬 파일을 동적으로 임포트하여 모든 모델 클래스를 로드합니다.
2. SQLAlchemy의 `inspect` 기능을 사용하여 실제 데이터베이스의 스키마 정보를 가져옵니다.
3. 로드된 모든 모델 클래스를 순회하며, 각 모델의 테이블 및 칼럼 정의가 DB 스키마와 일치하는지
   다음 항목들을 비교 검증합니다:
    - 테이블 존재 여부
    - 칼럼 존재 여부 (모델->DB, DB->모델 양방향)
    - 칼럼 데이터 타입
    - Null 허용 여부
"""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import pkgutil
import importlib

from src.common.database.db_connector import Base
from src.common.models.user import User # 세션 쿼리 테스트를 위한 기본 모델

# --- 동적 모델 임포트 --- #
def import_all_models():
    """
    `src.common.models` 패키지 내의 모든 모듈을 동적으로 임포트합니다.
    이를 통해 `Base.registry.mappers`가 모든 모델 클래스를 인식하게 됩니다.
    """
    models_package = importlib.import_module("src.common.models")
    for _, name, _ in pkgutil.iter_modules(models_package.__path__):
        if name != "__init__":
            importlib.import_module(f"src.common.models.{name}")

# 테스트 파일 로드 시점에 모든 모델을 임포트
import_all_models()


@pytest.fixture(scope="function")
def db_inspector(real_db: Session):
    """
    데이터베이스 스키마 정보를 조회할 수 있는 `Inspector` 객체를 생성하는 Fixture.
    """
    return inspect(real_db.bind)


def test_get_db_session(real_db: Session):
    """
    - **테스트 대상**: `real_db` Fixture
    - **목적**: 테스트에 사용되는 데이터베이스 세션이 정상적으로 생성되고, 간단한 쿼리를 실행할 수 있는지 확인합니다.
    - **시나리오**: `real_db`로부터 받은 세션 객체가 `Session` 타입인지 확인하고, 간단한 쿼리를 실행해 예외가 발생하는지 확인합니다.
    - **Mock 대상**: 없음
    """
    assert isinstance(real_db, Session)
    # 세션이 유효한지 간단한 쿼리로 확인
    real_db.query(User).first()


@pytest.mark.parametrize("model_class", [mapper.class_ for mapper in Base.registry.mappers])
def test_model_and_db_schema_match(real_db: Session, db_inspector, model_class):
    """
    - **테스트 대상**: 모든 SQLAlchemy 모델 클래스와 실제 DB 테이블 스키마
    - **목적**: 모델과 DB 스키마 간의 불일치가 없는지 검증합니다.
    - **시나리오**:
        1. `Base`에 등록된 모든 모델 클래스를 순회합니다.
        2. 각 모델에 대해, DB에 해당 테이블이 존재하는지 확인합니다.
        3. 모델의 모든 칼럼이 DB 테이블에 존재하는지, 타입과 Null 여부가 일치하는지 확인합니다.
        4. DB 테이블의 모든 칼럼이 모델에 정의되어 있는지 확인하여, 모델에 없는 불필요한 칼럼이 DB에 추가되었는지 검사합니다.
    - **Mock 대상**: 없음
    """
    if not hasattr(model_class, "__tablename__"):
        pytest.skip(f"Skipping {model_class.__name__}: Not a SQLAlchemy model with a __tablename__.")

    table_name = model_class.__tablename__

    # 1. 테이블 존재 여부 검증
    assert db_inspector.has_table(table_name), f"Table '{table_name}' does not exist in the database for model '{model_class.__name__}'."

    # 2. 모델과 DB의 칼럼 정보 가져오기
    model_columns = {col.name: col for col in model_class.__table__.columns}
    db_columns = {col['name']: col for col in db_inspector.get_columns(table_name)}

    # 3. 모델의 칼럼이 DB에 모두 존재하는지, 속성이 일치하는지 검증
    for col_name, model_col in model_columns.items():
        assert col_name in db_columns, f"Column '{col_name}' from model '{model_class.__name__}' not found in DB table '{table_name}'."
        db_col = db_columns[col_name]

        # 타입 검증 (DB 엔진별 타입 이름 차이를 고려한 단순 비교)
        model_type_str = str(model_col.type).split('(')[0]
        db_type_str = str(db_col['type']).split('(')[0]
        # 예: `String(100)` -> `String`, `VARCHAR(100)` -> `VARCHAR`
        # PostgreSQL의 `DOUBLE PRECISION`은 SQLAlchemy의 `FLOAT`에 해당
        assert model_type_str == db_type_str or \
               (model_type_str == "FLOAT" and db_type_str == "DOUBLE PRECISION") or \
               (model_type_str == "DATETIME" and db_type_str == "TIMESTAMP"), \
            f"Type mismatch for column '{col_name}' in table '{table_name}': Model='{model_type_str}', DB='{db_type_str}'"

        # Nullable 속성 검증 (Primary Key는 기본적으로 Not Null이므로 제외)
        if not model_col.primary_key:
            assert db_col['nullable'] == model_col.nullable, \
                f"Nullable mismatch for column '{col_name}' in table '{table_name}': Model='{model_col.nullable}', DB='{db_col['nullable']}'"

    # 4. DB의 칼럼이 모델에 모두 존재하는지 검증 (DB에 불필요한 칼럼이 있는지 확인)
    for col_name in db_columns:
        assert col_name in model_columns, f"Extra column '{col_name}' found in DB table '{table_name}' which is not defined in model '{model_class.__name__}'."
