import aiohttp
import asyncio
import logging
import zipfile
import io
from lxml import etree
from typing import List, Dict, Tuple, Optional
from ..core.database import db
from ..core.config import settings # API 키 사용을 위해 추가
import httpx

logger = logging.getLogger(__name__)

DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

async def get_corp_code_xml_content() -> Optional[bytes]:
    """DART에서 CORPCODE.xml 파일을 다운로드하고 압축 해제하여 내용을 반환"""
    api_url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={settings.DART_API_KEY}"
    logger.info(f"DART 고유번호 XML 다운로드 시작: {api_url}") # URL 로깅 (API 키 제외 필요 시 수정)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client: # 타임아웃 증가
            response = await client.get(api_url)
            response.raise_for_status() # HTTP 오류 발생 시 예외 발생

        zip_content = response.content
        if not zip_content:
            logger.error("DART API에서 빈 응답을 받았습니다.")
            return None
        logger.info(f"DART API로부터 ZIP 파일 다운로드 성공 (크기: {len(zip_content)} bytes)")

        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            if 'CORPCODE.xml' not in z.namelist():
                logger.error("ZIP 파일 내에 CORPCODE.xml이 없습니다.")
                return None
            with z.open('CORPCODE.xml') as xml_file:
                xml_content = xml_file.read()
                if not xml_content:
                     logger.warning("CORPCODE.xml 파일 내용은 비어있습니다.")
                     return None
                logger.info(f"CORPCODE.xml 압축 해제 성공 (크기: {len(xml_content)} bytes)")
                return xml_content

    except httpx.HTTPStatusError as e:
        logger.error(f"DART API 요청 실패: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        logger.error(f"DART API 요청 중 네트워크 오류: {e}")
        return None
    except zipfile.BadZipFile:
        logger.error("다운로드한 파일 처리 오류: 유효한 ZIP 파일이 아닙니다.")
        return None
    except Exception as e:
        logger.error(f"DART 고유번호 XML 처리 중 예상치 못한 오류: {e}", exc_info=True)
        return None

def parse_corp_code_xml(xml_content: bytes) -> List[Dict[str, str]]:
    """XML 내용을 파싱하여 기업 코드 리스트 반환"""
    logger.info("CORPCODE.xml 파싱 시작...")
    if not xml_content:
        logger.warning("파싱할 XML 내용이 없습니다.")
        return []
    try:
        root = etree.fromstring(xml_content)
        corp_data = []
        corp_elements = root.xpath('//list')
        for corp in corp_elements:
            corp_code = corp.xpath('./corp_code/text()')
            corp_name = corp.xpath('./corp_name/text()')
            stock_code = corp.xpath('./stock_code/text()')

            # 필수 데이터 확인
            if corp_code and corp_name:
                 data = {
                     'corp_code': corp_code[0].strip(),
                     'corp_name': corp_name[0].strip(),
                     # stock_code는 없을 수도 있음
                     'stock_code': stock_code[0].strip().replace('-', '') if stock_code and stock_code[0].strip() else None
                 }
                 # 주식 코드가 있는 경우만 추가 (6자리 숫자 형식 검사 추가 가능)
                 if data['stock_code'] and data['stock_code'].isdigit() and len(data['stock_code']) == 6:
                     corp_data.append(data)
                 elif not data['stock_code']:
                     # 주식 코드가 없는 DART 정보 (상장되지 않은 회사 등)는 로깅만 하고 넘어감
                     logger.debug(f"주식 코드 없는 DART 정보 건너뜀: {data['corp_name']} ({data['corp_code']})")
                 else:
                     logger.debug(f"유효하지 않은 주식 코드 형식 건너뜀: {data['stock_code']} ({data['corp_name']})")


        logger.info(f"CORPCODE.xml 파싱 완료. 유효한 주식 코드 보유 기업 수: {len(corp_data)}")
        if not corp_data:
             logger.warning("파싱 결과, 유효한 주식 코드를 가진 기업 데이터가 없습니다.")
        return corp_data
    except etree.XMLSyntaxError as e:
        logger.error(f"CORPCODE.xml 파싱 오류: {e}")
        return []
    except Exception as e:
        logger.error(f"XML 파싱 중 예상치 못한 오류: {e}", exc_info=True)
        return []

async def update_stocks_with_corp_data(corp_data: List[Dict[str, str]]) -> Tuple[int, int]:
    """파싱된 기업 데이터를 사용하여 DB의 stocks 테이블에 Upsert"""
    if not corp_data:
        logger.warning("DB 업데이트를 위한 기업 데이터가 없습니다.")
        return 0, 0

    inserted_count = 0
    updated_count = 0

    # --- 수정: DART 데이터 중 유효한 stock_code 가진 것만 필터링 ---
    valid_dart_data = [item for item in corp_data if item.get('stock_code')]
    if not valid_dart_data:
        logger.warning("DB 업데이트를 위한 유효한 DART 기업 데이터(stock_code 보유)가 없습니다.")
        return 0, 0
    # --------------------------------------------------------

    logger.info(f"DB Upsert 시작: {len(valid_dart_data)}개의 유효한 DART 기업 데이터 처리 시도...")

    async with db.pool.acquire() as conn:
        async with conn.transaction(): # 트랜잭션 시작
            # --- 수정: UPSERT 로직 ---
            # 임시 테이블 대신 직접 UPSERT 시도 (데이터 양이 많지 않다면 가능)
            # 데이터 양이 매우 많다면 임시 테이블 방식이 더 효율적일 수 있음
            upsert_query = """
                INSERT INTO stocks (code, name, corp_code)
                VALUES ($1, $2, $3)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    corp_code = EXCLUDED.corp_code
                WHERE
                    stocks.name IS DISTINCT FROM EXCLUDED.name OR
                    stocks.corp_code IS DISTINCT FROM EXCLUDED.corp_code
                RETURNING xmax -- INSERT 시 0, UPDATE 시 0 아님
            """
            try:
                # executemany와 유사하게 각 레코드에 대해 쿼리 실행 및 결과 집계
                # 참고: asyncpg는 executemany가 RETURNING을 직접 지원하지 않을 수 있음
                #       개별 execute로 처리하거나, 임시테이블+CTE 방식 사용 고려
                #       여기서는 각 레코드 처리 방식으로 구현 (데이터가 아주 많지 않다는 가정)

                results = []
                for item in valid_dart_data:
                     # RETURNING xmax를 사용하기 위해 execute 사용 (fetchrow도 가능)
                     result = await conn.fetchval(
                         upsert_query,
                         item['stock_code'], item['corp_name'], item['corp_code']
                     )
                     # fetchval은 값을 반환하거나 None을 반환 (update가 일어나지 않은 경우 등)
                     # xmax=0 (insert), xmax!=0 (update), None (no update needed)
                     results.append(result)

                inserted_count = sum(1 for r in results if r == 0)
                updated_count = sum(1 for r in results if r is not None and r != 0)

                logger.info(f"DB Upsert 완료: {inserted_count} 건 신규 삽입, {updated_count} 건 정보 갱신.")

            except Exception as e:
                 logger.error(f"stocks 테이블 Upsert 중 오류: {e}", exc_info=True)
                 return 0, 0 # 오류 시 롤백됨
            # -------------------------

    logger.info(f"DB Upsert 프로세스 완료. 삽입: {inserted_count}, 갱신: {updated_count}")
    return inserted_count, updated_count

async def update_corp_codes_from_dart() -> Tuple[int, int]:
    """DART에서 고유번호 정보를 가져와 DB Upsert 실행"""
    logger.info("DART 고유번호 정보 갱신 프로세스 시작...")
    xml_content = await get_corp_code_xml_content()

    if not xml_content:
        logger.error("DART 고유번호 XML 내용을 가져오지 못했습니다. 갱신 중단.")
        return 0, 0

    corp_data = parse_corp_code_xml(xml_content)
    if not corp_data:
        logger.warning("XML 파싱 결과 데이터가 없거나 유효한 데이터가 없습니다. 갱신 중단.")
        return 0, 0

    inserted, updated = await update_stocks_with_corp_data(corp_data)
    logger.info(f"DART 고유번호 정보 갱신 프로세스 완료. 삽입: {inserted}, 갱신: {updated}")
    return inserted, updated 