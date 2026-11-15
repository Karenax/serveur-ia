"""Response headers shared by the Agent gateway and desktop relay."""

AGENT_RESPONSE_HEADERS = (
    'Content-Type', 'Content-Length', 'Content-Disposition', 'Cache-Control',
    'X-Content-Type-Options', 'Content-Security-Policy', 'Accept-Ranges',
    'Content-Range', 'ETag', 'Last-Modified',
    'X-Agent-Source-Sha256', 'X-Agent-Values-Sha256', 'X-Agent-Link-Sha256',
    'X-Agent-Network-Published',
)
