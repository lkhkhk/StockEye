# `pytest`와 `unittest.mock`을 이용한 `httpx` Mocking 가이드

이 문서는 `pytest`와 `unittest.mock`을 사용하여 비동기 Python 애플리케이션의 `httpx` 클라이언트를 Mocking하는 가장 좋은 방법을 안내합니다.

## 문제 상황

`httpx.AsyncClient`를 사용하는 코드를 테스트할 때, `get`이나 `post` 같은 메서드를 Mocking해야 합니다. 이 과정에서 `AsyncMock`의 동작 방식을 정확히 이해하지 못하면 `TypeError: 'coroutine' object is not iterable` 또는 `AttributeError: 'coroutine' object has no attribute 'get'` 같은 오류가 발생하기 쉽습니다.

이러한 문제는 `httpx` 라이브러리의 비동기/동기 메서드 동작 방식과 `AsyncMock`의 특징이 어긋나면서 발생합니다.

*   `httpx.AsyncClient.get()`, `httpx.AsyncClient.post()`: `httpx.Response` 객체를 반환하는 **비동기(async) 메서드**입니다.
*   `httpx.Response.json()`, `httpx.Response.raise_for_status()`: **동기(sync) 메서드**입니다.

`AsyncMock` 객체의 모든 속성(attribute)은 특별히 설정하지 않는 한 기본적으로 `AsyncMock` 인스턴스가 됩니다. 즉, `mock_response = AsyncMock()`으로 객체를 만들면, `mock_response.json()` 역시 비동기 메서드처럼 동작하여 `httpx.Response`의 실제 동작과 달라집니다.

## 해결책: `AsyncMock`과 `MagicMock`의 올바른 사용

가장 안정적이고 명확한 해결책은 `with patch(...)` 구문과 함께 `AsyncMock`과 `MagicMock`을 역할에 맞게 명확히 구분하여 사용하는 것입니다.

### `AsyncMock` vs. `MagicMock`

*   **`MagicMock`**: **동기** 객체, 메서드, 함수를 Mocking할 때 사용합니다. `unittest.mock`의 표준 Mock 객체입니다.

*   **`AsyncMock`**: **비동기** 객체, 메서드, 함수를 Mocking하기 위해 설계되었습니다. `async/await` 구문과 함께 사용됩니다.
    *   `AsyncMock` 객체를 `await`하면 `return_value`가 반환됩니다.
    *   `AsyncMock` 객체의 메서드를 호출하면, 그 결과로 Coroutine이 반환됩니다. 이 Coroutine을 `await`해야 최종 `return_value`를 얻을 수 있습니다.
    *   **핵심:** `AsyncMock` 객체에 있는 특정 메서드를 **동기적으로 동작**하게 만들고 싶다면, 해당 속성을 `MagicMock` 인스턴스로 직접 교체해야 합니다.

### 최종 예시 코드

아래는 `httpx.AsyncClient`를 사용하는 함수를 테스트하는 가장 이상적인 예시입니다.

```python
# 테스트 대상 코드 (예: src/my_module.py)
import httpx

async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://example.com/api/data")
        response.raise_for_status()
        return response.json()

# 테스트 코드 (예: tests/test_my_module.py)
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.my_module import fetch_data

@pytest.mark.asyncio
async def test_fetch_data_success():
    # 1. with patch(...) 구문으로 httpx의 비동기 메서드를 Mocking
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        
        # 2. `get` 메서드의 반환 값으로 사용될 `response` 객체를 AsyncMock으로 생성
        mock_response = AsyncMock()
        mock_response.status_code = 200

        # 3. 동기 메서드인 `json()`과 `raise_for_status()`는 MagicMock으로 교체
        mock_response.json = MagicMock(return_value={"key": "value"})
        mock_response.raise_for_status = MagicMock()

        # 4. `get` 메서드가 반환할 Mock 객체 설정
        mock_get.return_value = mock_response

        # 5. 테스트 대상 함수 호출
        data = await fetch_data()

        # 6. 결과 및 Mock 객체 호출 검증
        assert data == {"key": "value"}
        mock_get.assert_awaited_once_with("https://example.com/api/data")
```

이 패턴을 따르면 `httpx`를 사용하는 비동기 코드를 안정적으로 테스트하고 일반적인 Mocking 관련 실수를 피할 수 있습니다.
