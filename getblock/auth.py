import keyring

from getblock.config import profile_name

SERVICE_NAME = "getblock-cli"
KEY_NAME = "getblock_api_key"
ADVANCED_KEY_NAME = "getblock_advanced_api_key"


def advanced_credential_name(profile):
    return ADVANCED_KEY_NAME if profile == "default" else f"{ADVANCED_KEY_NAME}:{profile_name(profile)}"


def save_advanced_api_key(api_key, profile="default"):
    keyring.set_password(SERVICE_NAME, advanced_credential_name(profile), api_key)


def get_advanced_api_key(profile="default"):
    return keyring.get_password(SERVICE_NAME, advanced_credential_name(profile))


def delete_advanced_api_key(profile="default"):
    try:
        keyring.delete_password(SERVICE_NAME, advanced_credential_name(profile))
    except keyring.errors.PasswordDeleteError:
        pass


def credential_name(profile):
    return KEY_NAME if profile == "default" else f"{KEY_NAME}:{profile_name(profile)}"


def save_api_key(api_key: str, profile="default"):
    keyring.set_password(SERVICE_NAME, credential_name(profile), api_key)


def get_api_key(profile="default"):
    return keyring.get_password(SERVICE_NAME, credential_name(profile))


def delete_api_key(profile="default"):
    try:
        keyring.delete_password(SERVICE_NAME, credential_name(profile))
    except keyring.errors.PasswordDeleteError:
        pass
