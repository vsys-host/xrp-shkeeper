import os
import json
import time
import decimal
import xrpl
from flask import current_app as app
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
from xrpl.core.addresscodec import is_valid_xaddress, is_valid_classic_address,xaddress_to_classic_address
from xrpl.models.requests.account_info import AccountInfo
from xrpl.models.requests.ledger_data import LedgerData
from xrpl.models.requests.ledger import Ledger
from xrpl.models.requests.tx import Tx
from xrpl.models.response import ResponseStatus
from xrpl.utils import drops_to_xrp
from .encryption import Encryption
from .config import config
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

    def set_fee_deposit_account(self):
        wallet = Wallet.create()    
        # Extract the address and secret from the wallet
        address = wallet.classic_address
        secret = wallet.seed
        e = Encryption
        try:
            from app import create_app
            app = create_app()
            app.app_context().push()
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
        try:
            pd = Accounts.query.filter_by(type = "fee_deposit").first()
        except:
            db.session.rollback()
            raise Exception(f"There was exception during query to the database, try again later")
        if not pd:
            self.set_fee_deposit_account()
        pd = Accounts.query.filter_by(type = "fee_deposit").first()
        return pd.address
    
    def get_fee_deposit_account_balance(self):
        try:
            pd = Accounts.query.filter_by(type = "fee_deposit").first()
        except:
            db.session.rollback()
            raise Exception(f"There was exception during query to the database, try again later")
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
        try:
            from app import create_app
            app = create_app()
            app.app_context().push()
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
        try:
            from app import create_app
            app = create_app()
            app.app_context().push()
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

    def get_all_addresses(self):
        address_list = []
        try:
            wallet_list = Wallets.query.all()
        except:
            db.session.rollback()
            raise Exception(f"There was exception during query to the database, try again later")
        for wallet in wallet_list:
            address_list.append(wallet.pub_address)
        return address_list
    
    def get_all_accounts(self):
        account_list = []
        try:
            all_account_list = Accounts.query.all()
        except:
            db.session.rollback()
            raise Exception(f"There was exception during query to the database, try again later")
        for account in all_account_list:
            account_list.append(account.address)
        return account_list
 
    def generate_wallet(self):
        wallet = Wallet.create()    
        # Extract the address and secret from the wallet
        address = wallet.classic_address
        secret = wallet.seed
        self.save_wallet_to_db(address, secret)    
        return address
    
    def get_balance(self, address):    
        # Create an AccountInfo request
        account_info_request = AccountInfo(
            account=address,
            ledger_index="validated"  # Use "validated" for the latest validated ledger
        )
    
        # Send the request and get the response
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
            from app import create_app
            app = create_app()
            app.app_context().push()
            try:
                pd = Accounts.query.filter_by(address = s_address).first()
            except:
                db.session.rollback()
                raise Exception(f"There was exception during query to the database, try again later")
            
            pd.amount = decimal.Decimal(s_amount)                     
            with app.app_context():
                db.session.add(pd)
                db.session.commit()
                db.session.close()
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
        try:
            pd = Wallets.query.filter_by(pub_address = address).first()
        except:
            db.session.rollback()
            raise Exception(f"There was exception during query to the database, try again later")
        e = Encryption()
        return e.decrypt(pd.priv_key)
    
    def make_multipayout(self, payout_list):
        payout_results = []
        payout_list = payout_list

        for payout in payout_list:
            payout.update({'dest_tag': None})
    
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
        should_pay = should_pay + len(payout_list) * (config('NETWORK_FEE')) + 10
        have_crypto = self.get_fee_deposit_account_balance()
        if have_crypto < should_pay:
            raise Exception(f"Have not enough crypto on fee account, need {should_pay} have {have_crypto}")
        else:
            sending_wallet = xrpl.wallet.Wallet.from_seed(self.get_seed_from_address(self.get_fee_deposit_account()))
            for payout in payout_list:
                payment = xrpl.models.transactions.Payment(
                        account=self.get_fee_deposit_account(),
                        amount=xrpl.utils.xrp_to_drops(int(payout['amount'])),
                        destination=payout['dest'],)
                				
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
            amount = account_balance - decimal.Decimal('0.00002') - decimal.Decimal('10')
            payment = xrpl.models.transactions.Payment(
                account=sending_wallet.address,
                amount=xrpl.utils.xrp_to_drops(int(amount)),
                destination=destination,
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
                
                payment = xrpl.models.transactions.AccountDelete(
                    account=sending_wallet.address,
                    destination=destination,
                )                
            else:
                logger.warning("To soon to delete account, need check some time: https://xrpl.org/accountdelete.html#error-cases")
                return False
        try:    
            response = xrpl.transaction.submit_and_wait(payment, self.client, sending_wallet)    
        except xrpl.transaction.XRPLReliableSubmissionException as e:   
            response = f"Submit failed: {e}"                
        logger.warning(response)        
        drain_results.append({
                        "dest": destination,
                        "amount": float(self.get_xrp_from_drops(response.result['meta']['delivered_amount'])),
                        "status": "success",
                        "txids": [response.result['hash']],
                    })
        logger.warning(drain_results)
        
        return drain_results
    

    
    
                                    
