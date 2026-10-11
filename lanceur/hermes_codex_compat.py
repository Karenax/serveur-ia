"""Codex OAuth request headers, scoped to the Fred-owned Hermes process.

The native SDK resolves key_cmd callables while preparing each request. Derive
the workspace headers afterwards, from that request's actual bearer, so token
rotation never leaves a previous account's headers on a reused client.
"""

# Kept as standalone source because the installed Hermes interpreter cannot
# import modules bundled inside Fred's executable. The same source is exercised
# by install() and injected into that interpreter before its gateway starts.
PATCH_SOURCE = r'''
def _fred_install_codex_headers():
    from functools import wraps
    from openai import OpenAI, AsyncOpenAI
    from agent.codex_headers import codex_cloudflare_headers, is_official_codex_base_url

    def apply(client, request):
        if not (is_official_codex_base_url(str(client.base_url))
                and is_official_codex_base_url(str(request.url))):
            return
        authorization = request.headers.get('Authorization', '')
        scheme, _, token = authorization.partition(' ')
        token = token.strip() if scheme.lower() == 'bearer' else ''
        # A rotation can remove a claim as well as change it. Clear previous
        # values before adding the headers derived from the actual bearer.
        for name in ('ChatGPT-Account-ID', 'x-openai-internal-codex-residency'):
            request.headers.pop(name, None)
        request.headers.update(codex_cloudflare_headers(token, base_url=str(client.base_url)))

    sync_original = OpenAI._prepare_request
    if not getattr(sync_original, '_fred_codex_headers', False):
        @wraps(sync_original)
        def prepare_sync(client, request):
            result = sync_original(client, request)
            apply(client, request)
            return result
        prepare_sync._fred_codex_headers = True
        OpenAI._prepare_request = prepare_sync

    async_original = AsyncOpenAI._prepare_request
    if not getattr(async_original, '_fred_codex_headers', False):
        @wraps(async_original)
        async def prepare_async(client, request):
            result = await async_original(client, request)
            apply(client, request)
            return result
        prepare_async._fred_codex_headers = True
        AsyncOpenAI._prepare_request = prepare_async
'''


def install():
    """Install the compatibility hooks in the current isolated interpreter."""
    namespace = {}
    exec(PATCH_SOURCE, namespace)
    namespace['_fred_install_codex_headers']()


GATEWAY_BOOTSTRAP = PATCH_SOURCE + '''
_fred_install_codex_headers()
import runpy
runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)
'''
