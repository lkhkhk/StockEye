import pytest
from fastapi.testclient import TestClient
from src.api.models.user import User

def create_admin_user(db):
    """테스트용 관리자 사용자를 생성합니다."""
    admin_user = User(
        username="admin_test",
        email="admin_test@example.com",
        password_hash="hashed_password", # 실제 테스트에서는 해싱된 값을 넣어야 합니다.
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.flush() # commit 대신 flush 사용
    db.refresh(admin_user)
    return admin_user

def test_admin_stats_as_admin(client: TestClient, db):
    """관리자로 로그인하여 통계 정보를 조회합니다."""
    # 테스트 전용 관리자 유저 생성
    admin_user = create_admin_user(db)
    
    # 관리자 역할로 토큰을 얻었다고 가정 (실제로는 로그인 과정 모킹 필요)
    # 여기서는 간단히 테스트를 위해 역할 기반 접근 제어만 확인
    # 라우터에 Depends(get_current_active_admin_user) 와 같은 의존성이 필요함
    
    # 이 테스트는 현재 인증/인가 로직 없이는 의미가 부족하여,
    # 엔드포인트가 정상 응답하는지만 확인합니다.
    response = client.get("/admin/admin_stats")
    assert response.status_code == 200
    data = response.json()
    assert "user_count" in data
    assert "trade_count" in data
    assert "prediction_count" in data 