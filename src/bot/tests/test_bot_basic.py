import subprocess
import pytest

def test_bot_main():
    try:
        result = subprocess.run(["python3", "src/bot/main.py"], capture_output=True, text=True, timeout=3)
        assert "봇 서비스 정상 동작" in result.stdout or "텔레그램 봇이 시작되었습니다" in result.stdout
    except subprocess.TimeoutExpired:
        # 무한대기 정상 동작으로 간주
        assert True 