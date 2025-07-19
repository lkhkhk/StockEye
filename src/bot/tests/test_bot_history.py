import subprocess

def test_bot_history():
    # 실제로는 mocking 또는 별도 테스트 서버 필요, 여기서는 구조 예시
    result = subprocess.run(["python3", "src/bot/main.py"], capture_output=True, text=True, input="/history\n")
    assert "예측 이력" in result.stdout or "예측 이력이 없습니다." in result.stdout 