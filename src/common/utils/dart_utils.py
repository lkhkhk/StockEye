import os
import logging
import httpx
import io
import zipfile
import lxml.etree as etree
from typing import List, Dict, Optional
from src.common.utils.http_client import get_retry_client
from src.common.utils.exceptions import DartApiError

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

async def dart_get_disclosures(
    corp_code: Optional[str] = None,
    api_key: Optional[str] = None,
    bgn_de: Optional[str] = None,
    end_de: Optional[str] = None,
    page_size: int = 100, # Renamed from max_count, set to DART's max
    test_page_limit: Optional[int] = None, # New parameter for testing
    last_rcept_no: Optional[str] = None # New parameter for optimization
) -> List[Dict[str, str]]:
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
    all_disclosures = []
    page_no = 1

    logger.debug(f"DART 공시 조회 시작: bgn_de={bgn_de}, end_de={end_de}, page_size={page_size}")

    async with get_retry_client() as client:
        while True:
            params = {
                "crtfc_key": api_key,
                "bgn_de": bgn_de,
                "end_de": end_de,
                "page_size": page_size, # Use page_size
                "page_no": page_no # Add page_no
            }
            if corp_code:
                params["corp_code"] = corp_code

            try:
                resp = await client.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                logger.debug(f"DART API 응답 (page_no={page_no}): {data}") # Added debug log
            except httpx.RequestError as e:
                logger.error(f"DART 공시 조회 API 요청 실패 (corp_code: {corp_code}, page_no: {page_no}): {e}", exc_info=True)
                raise DartApiError(f"DART API 요청 실패: {e}") from e

            status = data.get("status")
            message = data.get("message")
            current_page_list = data.get("list", [])

            if status != "000":
                # Handle specific status codes if necessary, e.g., '020' for usage limit
                logger.error(f"DART 공시 API가 오류를 반환했습니다. status: {status}, message: {message}, corp_code: {corp_code}, page_no: {page_no}")
                raise DartApiError(message, status_code=status)

            if not current_page_list:
                logger.debug(f"페이지 {page_no}에 더 이상 공시가 없습니다. (current_page_list is empty)")
                break # No more disclosures

            # Optimization: If last_rcept_no is provided, filter out older disclosures
            filtered_page_list = []
            found_older_disclosure = False
            for disclosure in current_page_list:
                if last_rcept_no and disclosure.get('rcept_no') <= last_rcept_no:
                    found_older_disclosure = True
                    logger.debug(f"이전 공시({disclosure.get('rcept_no')}) 발견. 조회 중단.")
                    break # Stop processing this page and break the loop
                filtered_page_list.append(disclosure)
            
            all_disclosures.extend(filtered_page_list)
            logger.debug(f"페이지 {page_no}에서 {len(filtered_page_list)}건의 공시를 추가했습니다. 현재까지 총 {len(all_disclosures)}건.")

            if found_older_disclosure:
                logger.debug("이전 공시를 발견하여 공시 조회를 조기에 중단합니다.")
                break # Break the main while loop
            
            # Check if this is the last page
            total_count = data.get("total_count", 0)
            # Use the actual page_count from the API response, which is consistently 10
            actual_page_items = data.get("page_count", 10) 
            total_page = (total_count + actual_page_items - 1) // actual_page_items
            logger.debug(f"total_count: {total_count}, total_page: {total_page}, current_page_no: {page_no}, actual_page_items: {actual_page_items}")

            if page_no >= total_page:
                logger.debug(f"마지막 페이지 ({total_page})에 도달했습니다. 공시 조회 종료.")
                break
            
            if test_page_limit is not None and page_no >= test_page_limit:
                logger.warning(f"TEST LIMIT: {test_page_limit} 페이지에 도달하여 공시 조회를 중단합니다.")
                break

            page_no += 1

    logger.debug(f"DART 공시 조회 완료. 최종 all_disclosures 길이: {len(all_disclosures)}")
    if all_disclosures:
        logger.debug(f"첫 5개 공시: {all_disclosures[:5]}")
        logger.debug(f"마지막 5개 공시: {all_disclosures[-5:]}")
    return all_disclosures