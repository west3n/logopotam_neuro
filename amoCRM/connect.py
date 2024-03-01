from amocrm.v2 import tokens
from decouple import config


CLIENT_ID = config('CLIENT_ID')
CLIENT_SECRET = config('CLIENT_SECRET')
AUTHORIZATION_CODE = config('AUTHORIZATION_CODE')
SUBDOMAIN = config('SUBDOMAIN')
REDIRECT_URL = config('REDIRECT_URL')


def amocrm_connect():
    tokens.default_token_manager(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        subdomain=SUBDOMAIN,
        redirect_url=REDIRECT_URL,
        storage=tokens.FileTokensStorage(),
    )
    tokens.default_token_manager.init(code=AUTHORIZATION_CODE, skip_error=True)


if __name__ == "__main__":
    amocrm_connect()
