import os
from decimal import Decimal

config = {

    'FULLNODE_URL': os.environ.get('FULLNODE_URL', 'https://s1.ripple.com:51234/'),
    'FULLNODE_TIMEOUT': os.environ.get('FULLNODE_TIMEOUT', '60'),
    'CHECK_NEW_BLOCK_EVERY_SECONDS': os.environ.get('CHECK_NEW_BLOCK_EVERY_SECONDS',2),
    'EVENTS_MAX_THREADS_NUMBER': int(os.environ.get('EVENTS_MAX_THREADS_NUMBER', 5)),
    'EVENTS_MIN_DIFF_TO_RUN_PARALLEL': int(os.environ.get('EVENTS_MIN_DIFF_TO_RUN_PARALLEL', 200)), #min difference between last checked block and last block in blockchain to run checking blocks in parallel mode
    'DEBUG': os.environ.get('DEBUG', False),
    'LOGGING_LEVEL': os.environ.get('LOGGING_LEVEL', 'INFO'),
    'SQLALCHEMY_DATABASE_URI' : os.environ.get('SQLALCHEMY_DATABASE_URI', "mariadb+pymysql://root:shkeeper@mariadb/xrp-shkeeper?charset=utf8mb4"),
    'SQLALCHEMY_POOL_SIZE' : os.environ.get('SQLALCHEMY_POOL_SIZE', 30),
    'SQLALCHEMY_TRACK_MODIFICATIONS' : os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS', True), 
    'API_USERNAME': os.environ.get('XRP_USERNAME', 'shkeeper'),
    'API_PASSWORD': os.environ.get('XRP_PASSWORD', 'shkeeper'),
    'SHKEEPER_KEY': os.environ.get('SHKEEPER_BACKEND_KEY', 'shkeeper'),
    'SHKEEPER_HOST': os.environ.get('SHKEEPER_HOST', 'shkeeper:5000'),
    'REDIS_HOST': os.environ.get('REDIS_HOST', 'localhost'),
    'CELERY_MAX_TASKS_PER_CHILD': os.environ.get('CELERY_MAX_TASKS_PER_CHILD', '10'), 
    'MIN_TRANSFER_THRESHOLD': Decimal(os.environ.get('MIN_TRANSFER_THRESHOLD', '0.1')),
    'UPDATE_BALANCES_EVERY_SECONDS': os.environ.get('UPDATE_BALANCES_EVERY_SECONDS', '3600'),
    'LAST_BLOCK_LOCKED': os.environ.get('LAST_BLOCK_LOCKED', "False"),
    'NETWORK_FEE': os.environ.get('NETWORK_FEE', "0.0005"), #in XRP
    'XADDRESS_MODE': os.environ.get('XADDRESS_MODE', "disabled"), # uses one address and destination tag, DO NOT enable if not sure!
    'XRP_NETWORK': os.environ.get('XRP_NETWORK', 'main'),  # main, testnet
       

}

def is_test_network():
    if config['XRP_NETWORK'] == 'main':
        return False
    else:
        return True
    

