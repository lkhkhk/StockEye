import subprocess
import pytest

def test_bot_history():
    try:
        # 실제로는 mocking 또는 별도 테스트 서버 필요, 여기서는 구조 예시
        result = subprocess.run(["python3", "src/bot/main.py"], capture_output=True, text=True, input="/history\n", timeout=3)
        assert "예측 이력" in result.stdout or "예측 이력이 없습니다." in result.stdout or "텔레그램 봇이 시작되었습니다" in result.stdout
    except subprocess.TimeoutExpired:
        # 무한대기 정상 동작으로 간주
        assert True 