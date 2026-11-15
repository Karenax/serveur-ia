"""Routes used by the paired Thunderbird extension."""

import re

PREFIX = '/v1/thunderbird/bridge/'


def bridge_route(path):
    if not path.startswith(PREFIX):
        return False
    suffix = path[len(PREFIX):]
    return suffix in {'heartbeat', 'configure', 'import', 'jobs/claim'} or bool(
        re.fullmatch(r'jobs/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/result', suffix))
