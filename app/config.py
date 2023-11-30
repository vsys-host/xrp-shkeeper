import os
from decimal import Decimal

config = {

    'FULLNODE_URL': os.environ.get('FULLNODE_URL', 'https://s1.altnet.rippletest.net:51234/'),
    'FULLNODE_TIMEOUT': os.environ.get('FULLNODE_TIMEOUT', '60'),
    'CHECK_NEW_BLOCK_EVERY_SECONDS': os.environ.get('CHECK_NEW_BLOCK_EVERY_SECONDS',2),
    'DEBUG': os.environ.get('DEBUG', False),
    'LOGGING_LEVEL': os.environ.get('LOGGING_LEVEL', 'INFO'),
    'SQLALCHEMY_DATABASE_URI' : os.environ.get('SQLALCHEMY_DATABASE_URI', "mariadb+pymysql://root:shkeeper@mariadb/xrp-shkeeper?charset=utf8mb4"),
    'SQLALCHEMY_POOL_SIZE' : os.environ.get('SQLALCHEMY_POOL_SIZE', 30),
    'SQLALCHEMY_TRACK_MODIFICATIONS' : os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', True), 
    'UPDATE_TOKEN_BALANCES_EVERY_SECONDS': int(os.environ.get('UPDATE_TOKEN_BALANCES_EVERY_SECONDS', 3600)),
    'API_USERNAME': os.environ.get('ETH_USERNAME', 'shkeeper'),
    'API_PASSWORD': os.environ.get('ETH_PASSWORD', 'shkeeper'),
    'SHKEEPER_KEY': os.environ.get('SHKEEPER_BACKEND_KEY', 'shkeeper'),
    'SHKEEPER_HOST': os.environ.get('SHKEEPER_HOST', 'shkeeper:5000'),
    'REDIS_HOST': os.environ.get('REDIS_HOST', 'localhost'),
    'MIN_TRANSFER_THRESHOLD': Decimal(os.environ.get('MIN_TRANSFER_THRESHOLD', '0.001')),
    'UPDATE_BALANCES_EVERY_SECONDS': os.environ.get('UPDATE_BALANCES_EVERY_SECONDS', '60'),
    'LAST_BLOCK_LOCKED': os.environ.get('LAST_BLOCK_LOCKED', "True"),
    'NETWORK_FEE': os.environ.get('NETWORK_FEE', "0.000012"), #in XRP
    'XADDRESS_MODE': os.environ.get('XADDRESS_MODE', "disabled"), # uses one address and destination tag, DO NOT enable if not sure!
    'XRP_NETWORK': os.environ.get('XRP_NETWORK', 'main'),  # main, testnet
       

}

def is_test_network():
    if config['XRP_NETWORK'] == 'main':
        return False
    else:
        return True
    

