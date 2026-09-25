import keyring

SERVICE_NAME = "getblock-cli"
KEY_NAME = "getblock_api_key"

def save_api_key(api_key: str):
    keyring.set_password(SERVICE_NAME, KEY_NAME, api_key)

def get_api_key():
    return keyring.get_password(SERVICE_NAME, KEY_NAME)

def delete_api_key():
    try:    
        keyring.delete_password(SERVICE_NAME, KEY_NAME)
    except keyring.errors.PasswordDeleteError:
        pass
