import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Encryption:

    encryption = None
    key = None

    @classmethod
    def encrypt(cls, cleartext):
        cls.encryption = True
        cls.key  = cls._get_key_from_password("shkeeper")
        return cls._encrypt(cleartext)

    @classmethod
    def decrypt(cls, ciphertext):
        return cls._decrypt(ciphertext)

    @classmethod
    def _get_key_from_password(cls, password: str):
        salt = b'Shkeeper4TheWin!'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=500_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))


    @classmethod
    def _encrypt(cls, cleartext: str):
        return base64.urlsafe_b64encode(Fernet(cls.key).encrypt(cleartext.encode())).decode()

    @classmethod
    def _decrypt(cls, ciphertext: str):
        return Fernet(cls.key).decrypt(base64.urlsafe_b64decode(ciphertext)).decode()
