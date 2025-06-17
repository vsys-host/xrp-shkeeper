class MockWallet:
    def get_all_accounts(self):
        return ['rAlice', 'rBob']

    def get_transaction_from_ledger(self, txid):
        class Resp:
            @property
            def result(self):
                return {
                    "Account": "rAlice",
                    "Destination": "rBob",
                    "meta": {"delivered_amount": "1234567"},
                    "ledger_index": 100
                }
        return Resp()

    def get_xrp_from_drops(self, drops):
        return float(drops) / 1_000_000

    def get_last_block_number(self):
        return 110


def get_transaction(txid, wallet):
    data = wallet.get_transaction_from_ledger(txid).result
    account = data["Account"]
    dest = data["Destination"]
    amount = wallet.get_xrp_from_drops(data["meta"]["delivered_amount"])
    ledger_index = data["ledger_index"]

    if account in wallet.get_all_accounts() and dest in wallet.get_all_accounts():
        tx_type = 'internal'
    elif dest in wallet.get_all_accounts():
        tx_type = 'receive'
    elif account in wallet.get_all_accounts():
        tx_type = 'send'
    else:
        tx_type = 'unknown'

    return [[dest, amount, ledger_index // 10, tx_type]]


def test_get_transaction_internal():
    wallet = MockWallet()
    result = get_transaction("fake123", wallet)
    assert result == [['rBob', 1.234567, 10, 'internal']]

def test_get_transaction_receive():
    class WalletReceive(MockWallet):
        def get_transaction_from_ledger(self, txid):
            class Resp:
                @property
                def result(self):
                    return {
                        "Account": "rEve",
                        "Destination": "rBob",
                        "meta": {"delivered_amount": "1000000"},
                        "ledger_index": 50
                    }
            return Resp()

    wallet = WalletReceive()
    result = get_transaction("fake123", wallet)
    assert result == [['rBob', 1.0, 5, 'receive']]

def test_get_transaction_send():
    class WalletSend(MockWallet):
        def get_transaction_from_ledger(self, txid):
            class Resp:
                @property
                def result(self):
                    return {
                        "Account": "rAlice",
                        "Destination": "rMallory",
                        "meta": {"delivered_amount": "2000000"},
                        "ledger_index": 80
                    }
            return Resp()

    wallet = WalletSend()
    result = get_transaction("fake123", wallet)
    assert result == [['rMallory', 2.0, 8, 'send']]

def test_get_transaction_unknown():
    class WalletUnknown(MockWallet):
        def get_transaction_from_ledger(self, txid):
            class Resp:
                @property
                def result(self):
                    return {
                        "Account": "rEve",
                        "Destination": "rMallory",
                        "meta": {"delivered_amount": "500000"},
                        "ledger_index": 30
                    }
            return Resp()

    wallet = WalletUnknown()
    result = get_transaction("fake123", wallet)
    assert result == [['rMallory', 0.5, 3, 'unknown']]


if __name__ == "__main__":
    test_get_transaction_internal()
    test_get_transaction_receive()
    test_get_transaction_send()
    test_get_transaction_unknown()
