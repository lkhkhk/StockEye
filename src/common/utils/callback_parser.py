import logging

logger = logging.getLogger(__name__)

def parse_pagination_callback_data(callback_data: str, expected_prefix: str) -> tuple[str, int]:
    """
    Parses pagination callback data in the format 'prefix:query_str:offset' or 'prefix_query_str_offset'.
    Raises ValueError if the format is invalid.
    """
    parts_colon = callback_data.split(':')
    parts_underscore = callback_data.split('_')

    if len(parts_colon) == 3 and parts_colon[0] == expected_prefix:
        query_str = parts_colon[1]
        offset = int(parts_colon[2])
        return query_str, offset
    elif len(parts_underscore) == 3 and parts_underscore[0] == expected_prefix:
        query_str = parts_underscore[1]
        offset = int(parts_underscore[2])
        return query_str, offset
    else:
        logger.error(f"Invalid pagination callback data format. Expected '{expected_prefix}:query_str:offset' or '{expected_prefix}_query_str_offset', got: {callback_data}")
        raise ValueError("Invalid pagination callback data format")