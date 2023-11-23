# import json
# from decimal import Decimal

from flask import current_app, g
# import decimal
# import requests

# from .. import events
from ..logging import logger
from . import api
from app import create_app
# from ..unlock_acc import get_account_password
from ..wallet import XRPWallet

app = create_app()
app.app_context().push()

@api.post("/generate-address")
def generate_new_address():   
    w = XRPWallet() 
    new_address = w.generate_wallet()
    return {'status': 'success', 'address': new_address}

@api.post('/balance')
def get_balance():
    w = XRPWallet()
    balance = w.get_fee_deposit_account_balance()
    return {'status': 'success', 'balance': balance}

@api.post('/status')
def get_status():
    w = XRPWallet()
    last_checked_block_number = w.get_last_checked_block_number()
    last_checked_block_timestamp =  w.get_ledger_data(last_checked_block_number).result['close_time']
    return {'status': 'success', 'last_block_timestamp': last_checked_block_timestamp}

@api.post('/transaction/<txid>')
def get_transaction(txid):
    w = XRPWallet()
    related_transactions = []
    try:
        list_accounts = w.get_all_accounts()
        transaction = w.get_transaction_from_ledger(txid).result
        if (transaction['Destination'] in list_accounts) and (transaction['Account'] in list_accounts):
            address = transaction["Destination"]
            category = 'internal'
        elif transaction['Destination'] in list_accounts:
            address = transaction["Destination"]
            category = 'receive'
        elif transaction['Account'] in list_accounts:                
            address = transaction["Account"]
            category = 'send'
        else:
            return {'status': 'error', 'msg': 'txid is not related to any known address'}
        amount = w.get_xrp_from_drops(transaction["Amount"]) 
        confirmations = int(w.get_last_block_number()) - int(transaction["ledger_index"])
        related_transactions.append([address, amount, confirmations, category])
    except Exception as e:
        return {f'status': 'error', 'msg': {e}}
    if not related_transactions:
        logger.warning(f"txid {txid} is not related to any known address for {g.symbol}")
        return {'status': 'error', 'msg': 'txid is not related to any known address'}        
    logger.warning(related_transactions)
    return related_transactions


@api.post('/dump')
def dump():
    # coin_inst = Coin("ETH")
    # fee_address = coin_inst.get_fee_deposit_account()
    # r = requests.get('http://'+config["ETHEREUM_HOST"]+':8081',  headers={'X-Shkeeper-Backend-Key': config["SHKEEPER_KEY"]})
    # key_list = r.text.split("href=\"")
    # for key in key_list:
    #     if (key.find(fee_address.lower()[2:])) != -1:
    #         fee_key=requests.get('http://'+config["ETHEREUM_HOST"]+':8081/'+str(key.split("\"")[0]),  headers={'X-Shkeeper-Backend-Key': config["SHKEEPER_KEY"]})
    # return fee_key.text
    pass

@api.post('/fee-deposit-account')
def get_fee_deposit_account():
    w = XRPWallet()
    return {'account': w.get_fee_deposit_account(), 
            'balance': w.get_fee_deposit_account_balance()}

@api.post('/get_all_addresses')
def get_all_addresses():
    w = XRPWallet()
    all_addresses_list = w.get_all_accounts()
    return all_addresses_list
    


    
