
import decimal
import time
import copy
import requests
from decimal import Decimal

from celery.schedules import crontab
from celery.utils.log import get_task_logger
import requests as rq

from . import celery
from .config import config
from .utils import skip_if_running
from .wallet import XRPWallet
from .logging import logger

logger = get_task_logger(__name__)

# @celery.task()
# def make_multipayout(symbol, payout_list, fee):
#     # if symbol == "ETH":
#     #     coint_inst = Coin(symbol)
#     #     payout_results = coint_inst.make_multipayout_eth(payout_list, fee)
#     #     post_payout_results.delay(payout_results, symbol)
#     #     return payout_results    
#     # elif symbol in config['TOKENS'][config["CURRENT_ETH_NETWORK"]].keys():
#     #     token_inst = Token(symbol)
#     #     payout_results = token_inst.make_token_multipayout(payout_list, fee)
#     #     post_payout_results.delay(payout_results, symbol)
#     #     return payout_results    
#     # else:
#     #     return [{"status": "error", 'msg': "Symbol is not in config"}]
#     pass


# @celery.task()
# def post_payout_results(data, symbol):
#     # while True:
#     #     try:
#     #         return requests.post(
#     #             f'http://{config["SHKEEPER_HOST"]}/api/v1/payoutnotify/{symbol}',
#     #             headers={'X-Shkeeper-Backend-Key': config['SHKEEPER_KEY']},
#     #             json=data,
#     #         )
#     #     except Exception as e:
#     #         logger.exception(f'Shkeeper payout notification failed: {e}')
#     #         time.sleep(10)
#     pass


@celery.task()
def walletnotify_shkeeper(symbol, txid):
    while True:
        try:
            r = rq.post(
                    f'http://{config["SHKEEPER_HOST"]}/api/v1/walletnotify/{symbol}/{txid}',
                    headers={'X-Shkeeper-Backend-Key': config['SHKEEPER_KEY']}
                )
            return r
        except Exception as e:
            logger.warning(f'Shkeeper notification failed for {symbol}/{txid}: {e}')
            time.sleep(10)

@celery.task()
def create_wallet(self):
    w = XRPWallet()
    address = w.generate_wallet()
    return address


@celery.task(bind=True)
@skip_if_running
def refresh_balances(self):
    updated = 0
    w = XRPWallet()
    address_list = w.get_all_addresses()
    account_list = w.get_all_accounts()
    address_set = set(address_list)
    account_set = set(account_list)
    if address_set != account_set:
        logger.warning(f'Set wallets not equal to set accounts')
        if address_set - account_set:
            address_list_to_add = address_set - account_set
            logger.warning(f'Adding addresses {address_list_to_add} to accounts table')
            for a_account in address_list_to_add:
                w.save_account_to_db(a_account)
            account_list = w.get_all_accounts()
        else:
            add = account_set - address_set
            logger.warning(f'There is {add} in accounts table but there is not in wallets table' )
    else:
        logger.warning(f'Tables in sync')

    for account in account_list:
        amount = w.get_balance(account)
        if w.set_balance(account, amount):
            updated =+ 1
    
    return updated


# @celery.task(bind=True)
# @skip_if_running
# def drain_account(self, symbol, account):
#     # logger.warning(f"Start draining from account {account} crypto {symbol}")
#     # # return False
#     # if symbol == "ETH":
#     #     inst = Coin(symbol)
#     #     destination = inst.get_fee_deposit_account()
#     #     results = inst.drain_account(account, destination)
#     # elif symbol in config['TOKENS'][config["CURRENT_ETH_NETWORK"]].keys():
#     #     inst = Token(symbol)
#     #     destination = inst.get_fee_deposit_account()
#     #     results = inst.drain_tocken_account(account, destination)
#     # else:
#     #     raise Exception(f"Symbol is not in config")
    
#     # return results
#     pass
        


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Update cached account balances
    sender.add_periodic_task(int(config['UPDATE_BALANCES_EVERY_SECONDS']), refresh_balances.s())
    


