import os
import logging
import httpx
import io
import zipfile
import lxml.etree as etree
from typing import List, Dict, Optional
from src.common.http_client import get_retry_client
from src.common.exceptions import DartApiError

logger = logging.getLogger(__name__)

async def dart_get_all_stocks(api_key: Optional[str] = None) -> List[Dict[str, str]]:
    """
    DART OpenAPI에서 CORPCODE.xml을 다운로드하여 전체 상장종목(6자리 종목코드 포함) 리스트 반환
    반환 예시: [{"symbol": "005930", "name": "삼성전자", "corp_code": "00126380"}, ...]
    """
    if api_key is None:
        api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise ValueError("DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다.")
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    try:
        async with get_retry_client() as client:
            resp = await client.get(url, timeout=60)
            resp.raise_for_status()
    except httpx.RequestError as e:
        logger.error(f"DART CORPCODE.xml 요청 실패: {e}", exc_info=True)
        raise DartApiError(f"DART API 요청 실패: {e}") from e
    zip_content = resp.content
    corp_data = []
    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
        if 'CORPCODE.xml' not in z.namelist():
            raise RuntimeError("ZIP 파일 내에 CORPCODE.xml이 없습니다.")
        with z.open('CORPCODE.xml') as xml_file:
            # Use iterparse for memory-efficient parsing
            for event, elem in etree.iterparse(xml_file, tag='list'):
                corp_code = elem.find('corp_code').text if elem.find('corp_code') is not None else None
                corp_name = elem.find('corp_name').text if elem.find('corp_name') is not None else None
                stock_code = elem.find('stock_code').text if elem.find('stock_code') is not None else None

                if corp_code and corp_name:
                    data = {
                        'corp_code': corp_code.strip(),
                        'name': corp_name.strip(),
                        'symbol': stock_code.strip() if stock_code else None
                    }
                    # 6자리 숫자 종목코드만 추가
                    if data['symbol'] and data['symbol'].isdigit() and len(data['symbol']) == 6:
                        corp_data.append(data)
                # Clear the element from memory to free up resources
                elem.clear()
    return corp_data

async def dart_get_disclosures(corp_code: str, api_key: Optional[str] = None, bgn_de: Optional[str] = None, end_de: Optional[str] = None, max_count: int = 10) -> List[Dict[str, str]]:
    """
    DART OpenAPI에서 특정 기업의 공시(list.json)를 조회하여 최근 공시 목록을 반환
    반환 예시: [{"corp_name": ..., "report_nm": ..., "rcept_no": ..., "rcept_dt": ..., ...}, ...]
    """
    import datetime
    if api_key is None:
        api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise ValueError("DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다.")
    if bgn_de is None:
        bgn_de = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d")
    if end_de is None:
        end_de = datetime.datetime.now().strftime("%Y%m%d")
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": max_count
    }
    if corp_code:
        params["corp_code"] = corp_code

    try:
        async with get_retry_client() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
    except httpx.RequestError as e:
        logger.error(f"DART 공시 조회 API 요청 실패 (corp_code: {corp_code}): {e}", exc_info=True)
        raise DartApiError(f"DART API 요청 실패: {e}") from e

    status = data.get("status")
    message = data.get("message")

    if status != "000":
        logger.error(f"DART 공시 API가 오류를 반환했습니다. status: {status}, message: {message}, corp_code: {corp_code}")
        raise DartApiError(message, status_code=status)

    return data.get("list", [])