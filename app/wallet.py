import os
import json
import decimal
import xrpl
import logging
import requests
from flask import current_app as app
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
from xrpl.core.addresscodec import is_valid_xaddress, is_valid_classic_address,xaddress_to_classic_address, classic_address_to_xaddress
from xrpl.models.requests.account_info import AccountInfo
from xrpl.models.requests.ledger_data import LedgerData
from xrpl.models.requests.ledger import Ledger
from xrpl.models.requests.tx import Tx
from xrpl.models.response import ResponseStatus
from xrpl.utils import drops_to_xrp
from .encryption import Encryption
from .config import config, is_test_network
from .models import Wallets, Accounts, Settings, db
from .logging import logger

WALLETS_DIRECTORY = "wallets"


class XRPWallet():

    def __init__(self) -> None:
        self.client = JsonRpcClient(config["FULLNODE_URL"])

    def get_xrp_from_drops(self, drops):
        return drops_to_xrp(str(drops))
        

    def get_ledger_data(self, ledger_index):
        ledger_request = Ledger(ledger_index=ledger_index, transactions=True)
        ledger_response = self.client.request(ledger_request)
        return ledger_response
    
    def get_all_transactions_from_ledger(self, ledger_index):
        ledger_request = Ledger(ledger_index=ledger_index, transactions=True, expand=True)
        ledger_response = self.client.request(ledger_request)
        transactions = ledger_response.result
        transactions = transactions['ledger']['transactions']
        return transactions

    def get_transaction_from_ledger(self, transaction_index):
        transaction_request = Tx(transaction=transaction_index)
        transaction_response = self.client.request(transaction_request)
        return transaction_response    

    def get_last_block_number(self):
        last_number = self.get_ledger_data("validated").result["ledger_index"]
        return last_number
    
    def get_last_checked_block_number(self):
        with app.app_context():
            pd = Settings.query.filter_by(name = 'last_block').first()    
        last_checked_block_number = int(pd.value)
        return last_checked_block_number
    
    def get_transaction_price(self):
        return config['NETWORK_FEE']
    
    def get_xaddress(self, destination_tag):
        xaddress = classic_address_to_xaddress(self.get_fee_deposit_account(), destination_tag, is_test_network())
        logger.warning(f'Get xaddress {xaddress} from fee-deposit account and dest_tag {destination_tag}')
        return xaddress

    def set_fee_deposit_account(self):
        wallet = Wallet.create()    
        # Extract the address and secret from the wallet
        address = wallet.classic_address
        secret = wallet.seed
        e = Encryption
        try:
            with app.app_context():
                db.session.add(Wallets(pub_address = address, 
                                        priv_key = e.encrypt(secret),
                                        type = "fee_deposit",
                                        ))
                db.session.add(Accounts(address = address, 
                                             crypto = "XRP",
                                             amount = 0,
                                             type = "fee_deposit"
                                             ))
                db.session.commit()
                db.session.close()
                db.engine.dispose() 
        finally:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()  

    def get_fee_deposit_account(self):
        tries = 3
        for i in range(tries):
            try:
                pd = Accounts.query.filter_by(type = "fee_deposit").first()
            except:
                if i < tries - 1: # i is zero indexed
                    db.session.rollback()
                    continue
                else:
                    db.session.rollback()
                    raise Exception(f"There was exception during query to the database, try again later")
            break

        if not pd:
            self.set_fee_deposit_account()
        pd = Accounts.query.filter_by(type = "fee_deposit").first()
        return pd.address
    
    def get_fee_deposit_account_balance(self):
        tries = 3
        for i in range(tries):
            try:
                pd = Accounts.query.filter_by(type = "fee_deposit").first()
            except:
                if i < tries - 1: # i is zero indexed
                    db.session.rollback()
                    continue
                else:
                    db.session.rollback()
                    raise Exception(f"There was exception during query to the database, try again later")
            break
        amount  = self.get_balance(pd.address)
        return amount



    def handle_success_response(self, response):
        result = response.result
        account_data = result.get("account_data", {})
        return account_data
    
    def handle_error_response(self, response):
        # Code to handle error response
        result = response.result
        error_code = result.get("error_code", "Unknown")
        error_message = result.get("error_message", "Unknown error")
        error = result.get("error", "Unknown")
        if error == "actNotFound":
            return {"Balance": 0, "Sequence": -1}
        else:
            return error_code, error_message
    
    def handle_response(self, response):
        if response.status == ResponseStatus.SUCCESS:
            return self.handle_success_response(response)
        elif response.status == ResponseStatus.ERROR:
            return self.handle_error_response(response)
        else:
            logger.warning("Unknown response status")   

    def save_wallet_to_db(self, address, secret):
        e = Encryption
        logger.warning(f'Saving wallet {address} to DB')
        try:
            with app.app_context():
                db.session.add(Wallets(pub_address = address, 
                                        priv_key = e.encrypt(secret),
                                        type = "regular",
                                        ))
                db.session.add(Accounts(address = address, 
                                             crypto = "XRP",
                                             amount = 0,
                                             ))
                db.session.commit()
                db.session.close()
                db.engine.dispose() 
        finally:
            with app.app_context():
                db.session.remove()
                db.engine.dispose() 

    def save_account_to_db(self, address):
        logger.warning(f'Saving account {address} to DB')
        try:
            with app.app_context():
                db.session.add(Accounts(address = address, 
                                             crypto = "XRP",
                                             amount = 0,
                                             ))
                db.session.commit()
                db.session.close()
                db.engine.dispose() 
        finally:
            with app.app_context():
                db.session.remove()
                db.engine.dispose() 

    def get_dump(self):
        logger.warning('Start dumping wallets')
        all_wallets = {}
        address_list = self.get_all_addresses()
        for address in address_list:
            all_wallets.update({address: {'public_address': address,
                                          'secret': self.get_seed_from_address(address)}})
        return all_wallets

    def get_all_addresses(self):
        address_list = []
        tries = 3
        for i in range(tries):
            try:
                wallet_list = Wallets.query.all()
            except:
                if i < tries - 1: # i is zero indexed
                    db.session.rollback()
                    continue
                else:
                    db.session.rollback()
                    raise Exception(f"There was exception during query to the database, try again later")
            break
        for wallet in wallet_list:
            address_list.append(wallet.pub_address)
        return address_list
    
    def get_all_accounts(self):
        account_list = []
        tries = 3
        for i in range(tries):
            try:
                all_account_list = Accounts.query.all()
            except:
                if i < tries - 1: # i is zero indexed
                    db.session.rollback()
                    continue
                else:
                    db.session.rollback()
                    raise Exception(f"There was exception during query to the database, try again later")
            break
        for account in all_account_list:
            account_list.append(account.address)
        return account_list
    
    def get_next_destination_tag(self):
        if (not Settings.query.filter_by(name = "destination_tag").first()):
            logger.warning(f"Create destination_tag, because cannot get it in DB")
            try:
                with app.app_context():
                    db.session.add(Settings(name = "destination_tag", 
                                            value = 1000))
                    db.session.commit()
                    db.session.close() 
                    db.session.remove()
                    db.engine.dispose()
            finally:
                with app.app_context():
                    db.session.remove()
                    db.engine.dispose() 
            
        else:
            logger.warning('Destination tag exist in db, getting it ')
            tries = 3
            for i in range(tries):
                try:
                    pd = Settings.query.filter_by(name = "destination_tag").first()
                except:
                    if i < tries - 1: # i is zero indexed
                        db.session.rollback()
                        continue
                    else:
                        db.session.rollback()
                        raise Exception(f"There was exception during query to the database, try again later")
                break
            logger.warning(f'Get destination tag - {pd.value}')
            dest_tag = int(pd.value) + 1
            pd.value = str(dest_tag)
            logger.warning(f'Get a next destination tag {dest_tag}')
            try:
                with app.app_context():
                    db.session.add(pd)
                    db.session.commit()
                    db.session.close() 
                    db.session.remove()
                    db.engine.dispose()
            finally:
                with app.app_context():
                    db.session.remove()
                    db.engine.dispose() 
            return dest_tag        

    def generate_wallet(self):
        if config['XADDRESS_MODE'] == 'disabled':
            wallet = Wallet.create()    
            # Extract the address and secret from the wallet
            address = wallet.classic_address
            secret = wallet.seed
            self.save_wallet_to_db(address, secret)    
            return address
        else:
            address = classic_address_to_xaddress(self.get_fee_deposit_account(), self.get_next_destination_tag(), is_test_network()) 
            return address
    
    def get_balance(self, address):    
        # Create an AccountInfo request
        account_info_request = AccountInfo(
            account=address,
            ledger_index="validated"  # Use "validated" for the latest validated ledger
        )
    
        # Send the request and get the response
        requests_log = logging.getLogger("httpx")
        requests_log.setLevel(logging.WARNING)
        response = self.client.request(account_info_request)
        account_data = self.handle_response(response)
        # Extract the XRP balance from the response
        balance_xrp = drops_to_xrp(str(account_data["Balance"]))
    
        return balance_xrp
    
    def get_sequence_number(self, address):
        # Create an AccountInfo request
        account_info_request = AccountInfo(
            account=address,
            ledger_index="validated"  # Use "validated" for the latest validated ledger
        )
    
        # Send the request and get the response
        response = self.client.request(account_info_request)
        account_data = self.handle_response(response)
        # Extract the XRP balance from the response
        logger.warning(account_data)
        sequence = str(account_data["Sequence"])
    
        return sequence
    
    def set_balance(self, s_address, s_amount):
        try:
            tries = 3
            for i in range(tries):
                try:
                    pd = Accounts.query.filter_by(address = s_address).first()
                except:
                    if i < tries - 1: # i is zero indexed
                        db.session.rollback()
                        continue
                    else:
                        db.session.rollback()
                        raise Exception(f"There was exception during query to the database, try again later")
                break
            
            pd.amount = decimal.Decimal(s_amount)                     
            with app.app_context():
                db.session.add(pd)
                db.session.commit()
                db.session.close()
                db.session.remove()
                db.engine.dispose()  
        finally:
            with app.app_context():
                db.session.close()
                db.session.remove()
                db.engine.dispose()  
                
        return True

    
    def load_wallet_from_file(self, filename):
        with open(filename, 'r') as file:
            wallet_data = json.load(file)
        return wallet_data
    
    def load_all_wallets(self):
        wallets = []
        if os.path.exists(WALLETS_DIRECTORY):
            for filename in os.listdir(WALLETS_DIRECTORY):
                if filename.endswith(".json"):
                    file_path = os.path.join(WALLETS_DIRECTORY, filename)
                    wallet_data = self.load_wallet_from_file(file_path)
                    wallets.append(wallet_data)
        return wallets
    
    def get_seed_from_address(self, address):
        tries = 3
        for i in range(tries):
            try:
                pd = Wallets.query.filter_by(pub_address = address).first()
            except:
                if i < tries - 1: # i is zero indexed
                    db.session.rollback()
                    continue
                else:
                    db.session.rollback()
                    raise Exception(f"There was exception during query to the database, try again later")
            break
        return Encryption.decrypt(pd.priv_key)
    
    def make_multipayout(self, payout_list):
        payout_results = []
        payout_list = payout_list

        for payout in payout_list:
            if 'dest_tag' not in payout:
                payout.update({'dest_tag': None})
            else:
                payout.update({'dest_tag': int(payout['dest_tag'])})
    
        for payout in payout_list:
            if not is_valid_xaddress(payout['dest']) and not is_valid_classic_address(payout['dest']):
                raise Exception(f"Address {payout['dest']} is not valid XRPL address") 
            
            if not is_valid_classic_address(payout['dest']):
                    logger.warning(f"Provided address {payout['dest']} is not classic address, converting to classic address")
                    logger.warning(xaddress_to_classic_address(payout['dest']))
                    payout['dest'], payout['dest_tag'], is_testnet = xaddress_to_classic_address(payout['dest'])                   
                    logger.warning(f"Changed to {payout['dest']} which is classic address with destination tag {payout['dest_tag']}") 
         
        # Check if enouth funds for multipayout on account
        should_pay  = decimal.Decimal(0)
        for payout in payout_list:
            should_pay = should_pay + decimal.Decimal(payout['amount'])
        should_pay = should_pay + len(payout_list) * decimal.Decimal(config['NETWORK_FEE']) + decimal.Decimal(config['ACCOUNT_RESERVED_AMOUNT'])
        have_crypto = self.get_fee_deposit_account_balance()
        if have_crypto < should_pay:
            raise Exception(f"Have not enough crypto on fee account, need {should_pay} have {have_crypto}")
        else:
            sending_wallet = xrpl.wallet.Wallet.from_seed(self.get_seed_from_address(self.get_fee_deposit_account()))
            current_index = self.get_last_block_number()
            last_ledger_seq = int(current_index) + int(config['LEDGERS_TO_WAIT'])
            for payout in payout_list:
                payment = xrpl.models.transactions.Payment(
                        account=self.get_fee_deposit_account(),
                        amount=xrpl.utils.xrp_to_drops(decimal.Decimal(payout['amount'])),
                        destination=payout['dest'],
                        destination_tag=payout['dest_tag'],
                        fee=xrpl.utils.xrp_to_drops(decimal.Decimal(config['NETWORK_FEE'])),
                        last_ledger_sequence=last_ledger_seq)                 				
                try:    
                    response = xrpl.transaction.submit_and_wait(payment, self.client, sending_wallet)    
                except xrpl.transaction.XRPLReliableSubmissionException as e:   
                    response = f"Submit failed: {e}"                
                logger.warning(response)            
                payout_results.append({
                    "dest": payout['dest'],
                    "amount": float(payout['amount']),
                    "status": "success",
                    "txids": [response.result['hash']], 
                })

        
            return payout_results


    
    def drain_account(self, account_address, destination):
        #TODO stop draining if fee deposit account has 0 in the balance
        drain_results = []
        account_balance = decimal.Decimal(0)
        if not is_valid_xaddress(destination) and not is_valid_classic_address(destination):
            raise Exception(f"Address {destination} is not valid XRPL address") 

        if not is_valid_xaddress(account_address) and not is_valid_classic_address(account_address):
            raise Exception(f"Address {account_address} is not valid XRPL address")  
        
        if not is_valid_classic_address(destination):
                logger.warning(f"Provided address {destination} is not classic address, converting to classic address")
                logger.warning(xaddress_to_classic_address(destination))
                destination, dest_tag, is_testnet = xaddress_to_classic_address(destination)
                logger.warning(f"Changed to {destination} which is classic address with destination tag {dest_tag}") 

        if account_address == destination:
           logger.warning(f"Fee-deposit account, skip")
           return False
                
        sending_wallet = xrpl.wallet.Wallet.from_seed(self.get_seed_from_address(account_address))

        if account_address == self.get_fee_deposit_account():
            logger.warning("Draining fee-deposit account")
            account_balance = self.get_balance(account_address)
            amount = account_balance - decimal.Decimal(config['NETWORK_FEE']) - decimal.Decimal(config['ACCOUNT_RESERVED_AMOUNT'])
            current_index = self.get_last_block_number()
            last_ledger_seq = int(current_index) + int(config['LEDGERS_TO_WAIT'])
            payment = xrpl.models.transactions.Payment(
                account=sending_wallet.address,
                amount=xrpl.utils.xrp_to_drops(decimal.Decimal(amount)),
                destination=destination,
                fee=xrpl.utils.xrp_to_drops(decimal.Decimal(config['NETWORK_FEE'])),
                last_ledger_sequence=last_ledger_seq 
            )

            logger.warning(xrpl.account.get_latest_transaction(account_address, self.client).result)
        else:    
            logger.warning("Draining regular one time account, calling delete account")
            logger.warning(f"Account sequence number - {self.get_sequence_number(account_address)}")
            logger.warning(f"Last number in blockchain {self.get_last_block_number()}")
            if int(self.get_sequence_number(account_address)) < 0:
                   logger.warning(f"Account {account_address} has already drained, balance 0")
                   return False
            if int(self.get_last_block_number()) - int(self.get_sequence_number(account_address)) > 256:
                logger.warning(f"Account {account_address} can be deleted")

                current_index = self.get_last_block_number()
                last_ledger_seq = int(current_index) + int(config['LEDGERS_TO_WAIT'])
                
                payment = xrpl.models.transactions.AccountDelete(
                    account=sending_wallet.address,
                    destination=destination,
                    fee=xrpl.utils.xrp_to_drops(decimal.Decimal(config['DELETE_ACCOUNT_FEE'])),
                    last_ledger_sequence=last_ledger_seq 
                )                
            else:
                logger.warning("To soon to delete account, need wait some time: https://xrpl.org/accountdelete.html#error-cases")
                return False
        try:    
            response = xrpl.transaction.submit_and_wait(payment, self.client, sending_wallet, check_fee=False)    
        except Exception as e:   
            response = f"Submit failed: {e}"  
            logger.warning(e)              
        logger.warning(response)        
        drain_results.append({
                        "dest": destination,
                        "amount": float(self.get_xrp_from_drops(response.result['meta']['delivered_amount'])),
                        "status": "success",
                        "txids": [response.result['hash']],
                    })
        logger.warning(drain_results)
        
        return drain_results
    

    
    
                                    
