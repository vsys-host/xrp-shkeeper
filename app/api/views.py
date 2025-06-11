from flask import current_app, g
from flask import request
from ..logging import logger
from ..config import config, is_read_mode
from . import api
from app import create_app
from ..wallet import XRPWallet

app = create_app()
app.app_context().push()

@api.post("/generate-address")
def generate_new_address():
    data = request.get_json(silent=True) or {}
    xpub_str = data.get("xpub")
    w = XRPWallet() 
    new_address = w.generate_wallet(xpub_str)
    logger.warning(new_address)
    return {'status': 'success', 'address': new_address}

@api.post('/balance')
def get_balance():
    w = XRPWallet()
    if is_read_mode():
        balance = w.get_read_mode_deposit_account_balance()
    else:
      balance = w.get_fee_deposit_account_balance()
    return {'status': 'success', 'balance': balance}

@api.post('/status')
def get_status():
    w = XRPWallet()
    last_checked_block_number = w.get_last_checked_block_number()
    last_checked_block_timestamp =  w.get_ledger_data(last_checked_block_number).result['ledger']['close_time']
    return {'status': 'success', 'last_block_timestamp': last_checked_block_timestamp}

@api.post('/transaction/<txid>')
def get_transaction(txid):
    w = XRPWallet()
    related_transactions = []
    try:
        list_accounts = w.get_all_accounts()
        transaction = w.get_transaction_from_ledger(txid).result
        logger.warning(transaction)
        if (transaction['Destination'] in list_accounts) and (transaction['Account'] in list_accounts):
            address = transaction["Destination"]
            category = 'internal'
        elif transaction['Destination'] in list_accounts:
            if config['XADDRESS_MODE'] == 'disabled':
                address = transaction["Destination"]
                category = 'receive'
            else:
                if 'DestinationTag' in transaction:
                     dest_tag = int(transaction['DestinationTag'])
                     address = w.get_xaddress(dest_tag)
                else:
                     address = transaction["Destination"]
                category = 'receive'
        elif transaction['Account'] in list_accounts:                
            address = transaction["Account"]
            category = 'send'
        else:
            logger.warning({'status': 'error', 'msg': 'txid is not related to any known address'})
            return {'status': 'error', 'msg': 'txid is not related to any known address'}
        amount = w.get_xrp_from_drops(transaction["Amount"]) 
        confirmations = int(w.get_last_block_number()) - int(transaction["ledger_index"])
        related_transactions.append([address, amount, confirmations, category])
    except Exception as e:
        logger.warning({f'status': 'error', 'msg': {e}})
        return {f'status': 'error', 'msg': {e}}
    if not related_transactions:
        logger.warning(f"txid {txid} is not related to any known address for {g.symbol}")
        return {'status': 'error', 'msg': 'txid is not related to any known address'}        
    logger.warning(related_transactions)
    return related_transactions


@api.post('/dump')
def dump():
    w = XRPWallet()
    all_wallets = w.get_dump()
    return all_wallets

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
