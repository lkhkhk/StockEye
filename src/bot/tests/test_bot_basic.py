import subprocess

def test_bot_main():
    result = subprocess.run(["python3", "src/bot/main.py"], capture_output=True, text=True)
    assert "봇 서비스 정상 동작" in result.stdout 