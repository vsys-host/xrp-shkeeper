import time

from collections import defaultdict
from .models import Settings, db
from .logging import logger
from .config import config
from .wallet import XRPWallet
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

w = XRPWallet()

def handle_event(transaction):        
    logger.info(f'new transaction: {transaction!r}')


def log_loop(last_checked_block, check_interval):
    from .tasks import walletnotify_shkeeper #, drain_account
    from app import create_app
    app = create_app()
    app.app_context().push()

    while True:
        list_accounts = w.get_all_accounts()
        set_accounts = set(list_accounts)
        last_block = w.get_last_block_number()
        if last_checked_block == '' or last_checked_block is None:
            last_checked_block = last_block

        if last_checked_block > last_block:
            logger.exception(f'Last checked block {last_checked_block} is bigger than last block {last_block} in blockchain')
        elif last_checked_block == last_block - 2:
            pass
        elif (last_block - last_checked_block) > int(config['EVENTS_MIN_DIFF_TO_RUN_PARALLEL']):
            def check_in_parallel(block):
                try:
                    logger.warning(f"now checking in parallel block {block}")
                    transactions = w.get_all_transactions_from_ledger(block)
                    for tx in transactions:
                        if tx['TransactionType'] == "Payment":
                             if tx['Account'] in set_accounts or tx['Destination'] in set_accounts :
                                logger.warning(f"Found related transaction {tx['hash']}")
                                walletnotify_shkeeper.delay('XRP', tx['hash'])
                except Exception as e:
                    logger.exception(f'Block {block}: Failed to scan: {e}')
                    return False
                return True
            
            with ThreadPoolExecutor(max_workers=config['EVENTS_MAX_THREADS_NUMBER']) as executor:
                 while True:
                    blocks = []
                    try:
                        if last_block - last_checked_block < int(config['EVENTS_MIN_DIFF_TO_RUN_PARALLEL']):
                            break
                        for i in range(int(config['EVENTS_MAX_THREADS_NUMBER'])):
                            blocks.append(last_checked_block + 1 + i)
                        start_time = time.time()
                        results = list(executor.map(check_in_parallel, blocks))
                        logger.debug(f'Block chunk {blocks[0]} - {blocks[-1]} processed for {time.time() - start_time} seconds')
    
                        if all(results):
                            logger.debug(f"Commiting chunk {blocks[0]} - {blocks[-1]}")
                            last_checked_block = blocks[-1]
                            pd = Settings.query.filter_by(name = "last_block").first()
                            pd.value = last_checked_block
                            with app.app_context():
                                db.session.add(pd)
                                db.session.commit()
                                db.session.close()
                        else:
                            logger.info(f"Some blocks failed, retrying chunk {blocks[0]} - {blocks[-1]}")

                    except Exception as e:
                        sleep_sec = 60
                        logger.exception(f"Exception in main block scanner loop: {e}")
                        logger.warning(f"Waiting {sleep_sec} seconds before retry.")
                        time.sleep(sleep_sec)
    
        else:            
            for x in range(last_checked_block + 1, last_block):
                logger.warning(f"now checking block {x}")
                transactions = w.get_all_transactions_from_ledger(x)
                for tx in transactions:
                    if tx['TransactionType'] == "Payment":
                         if tx['Account'] in set_accounts or tx['Destination'] in set_accounts :
                            logger.warning(f"Found related transaction {tx['hash']}")
                            walletnotify_shkeeper.delay('XRP', tx['hash'])

                last_checked_block = x 
        
                pd = Settings.query.filter_by(name = "last_block").first()
                pd.value = x
                with app.app_context():
                    db.session.add(pd)
                    db.session.commit()
                    db.session.close()
        
        time.sleep(check_interval)
    
        
def events_listener():

    from app import create_app
    app = create_app()
    app.app_context().push()

    if (not Settings.query.filter_by(name = "last_block").first()) and (config['LAST_BLOCK_LOCKED'].lower() != 'true'):
        logger.warning(f"Changing last_block to a last block on a fullnode, because cannot get it in DB")
        with app.app_context():
            db.session.add(Settings(name = "last_block", 
                                         value = w.get_last_block_number()))
            db.session.commit()
            db.session.close() 
            db.session.remove()
            db.engine.dispose()
    
    while True:
        try:
            pd = Settings.query.filter_by(name = "last_block").first()
            last_checked_block = int(pd.value)
            log_loop(last_checked_block, int(config["CHECK_NEW_BLOCK_EVERY_SECONDS"]))
        except Exception as e:
            sleep_sec = 60
            logger.exception(f"Exception in main block scanner loop: {e}")
            logger.warning(f"Waiting {sleep_sec} seconds before retry.")
            time.sleep(sleep_sec)
    
