"""HTTPS-only redirects for public runtime downloads."""
import urllib.request

class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'):
            raise ValueError('Redirection non sécurisée.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)
