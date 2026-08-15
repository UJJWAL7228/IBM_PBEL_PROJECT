# ============================================================
# TRANSACTIONS MODULE
# AI FRAUD DETECTION SYSTEM
# ============================================================

transactions = []


def clear_transactions():
    transactions.clear()


def get_transactions():
    return transactions


def add_transaction(transaction):

    if isinstance(transaction, dict):
        transactions.append(transaction)


def set_transactions(transaction_list):

    transactions.clear()

    if isinstance(transaction_list, list):
        transactions.extend(transaction_list)