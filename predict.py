import os
import pandas as pd
import numpy as np


# ============================================================
# FAST HELPERS
# ============================================================

def clean_number(value, default=0.0):

    try:
        if value is None:
            return default

        if isinstance(value, (int, float, np.number)):
            if pd.isna(value):
                return default
            return float(value)

        text = str(value).strip()

        if not text:
            return default

        text = (
            text
            .replace(",", "")
            .replace("₹", "")
            .replace("$", "")
            .replace("€", "")
            .replace("%", "")
            .strip()
        )

        return float(text)

    except (ValueError, TypeError):
        return default


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_column_name(name):

    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def build_lookup(columns):

    return {
        normalize_column_name(column): column
        for column in columns
    }


# ============================================================
# RESOLVED COLUMN LOOKUP
# ============================================================

def build_resolved_lookup(columns):

    lookup = build_lookup(columns)

    def resolve(names, default=None):

        for name in names:

            normalized = normalize_column_name(name)

            column = lookup.get(normalized)

            if column is not None:
                return column

        return default

    resolved = {

        # ----------------------------------------------------
        # BASIC
        # ----------------------------------------------------

        "id": resolve([
            "transaction_id",
            "TransactionID",
            "Transaction_ID",
            "Transaction Id",
            "transactionId",
            "txn_id",
            "TxnID",
            "id",
            "ID"
        ]),

        "customer_name": resolve([
            "customer_name",
            "CustomerName",
            "Customer_Name",
            "Customer",
            "customer",
            "name",
            "Name"
        ]),

        # ----------------------------------------------------
        # AMOUNT
        # ----------------------------------------------------

        "amount": resolve([
            "amount",
            "Amount",
            "Amount_INR",
            "Amount INR",
            "TransactionAmount",
            "Transaction_Amount",
            "Transaction Amount",
            "transaction_amount",
            "transaction amount",
            "value",
            "Value"
        ]),

        # ----------------------------------------------------
        # PAYMENT
        # ----------------------------------------------------

        "payment_method": resolve([
            "payment_method",
            "PaymentMethod",
            "Payment_Method",
            "payment type",
            "payment_type",
            "PaymentType",
            "Payment Type",
            "payment",
            "Payment"
        ]),

        # ----------------------------------------------------
        # CHANNEL
        # ----------------------------------------------------

        "app_channel": resolve([
            "app_channel",
            "AppChannel",
            "App_Channel",
            "channel",
            "Channel",
            "app",
            "App",
            "payment_app",
            "PaymentApp"
        ]),

        # ----------------------------------------------------
        # MERCHANT
        # ----------------------------------------------------

        "merchant": resolve([
            "merchant",
            "Merchant",
            "company_merchant",
            "CompanyMerchant",
            "Company_Merchant",
            "MerchantName",
            "Merchant_Name",
            "merchant_name",
            "shop",
            "Shop",
            "store",
            "Store"
        ]),

        # ----------------------------------------------------
        # TRANSACTION TYPE
        # ----------------------------------------------------

        "transaction_type": resolve([
            "transaction_type",
            "TransactionType",
            "Transaction_Type",
            "Transaction Type",
            "type",
            "Type",
            "payment_type",
            "PaymentType"
        ]),

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        "location": resolve([
            "location",
            "Location",
            "city",
            "City",
            "transaction_location",
            "TransactionLocation"
        ]),

        # ----------------------------------------------------
        # DATE / TIME
        # ----------------------------------------------------

        "time": resolve([
            "datetime",
            "DateTime",
            "date_time",
            "Date_Time",
            "transaction_datetime",
            "TransactionDateTime",
            "Transaction_DateTime",
            "transaction_date_time",
            "Transaction Date Time",
            "time",
            "Time",
            "transaction_time",
            "TransactionTime"
        ]),

        # ----------------------------------------------------
        # BANK
        # ----------------------------------------------------

        "bank_name": resolve([
            "BankName",
            "Bank_Name",
            "bank_name",
            "Bank"
        ]),

        # ----------------------------------------------------
        # ACCOUNT TYPE
        # ----------------------------------------------------

        "account_type": resolve([
            "AccountType",
            "Account_Type",
            "account_type"
        ]),

        # ----------------------------------------------------
        # ACCOUNT NUMBER
        # ----------------------------------------------------

        "account_number": resolve([
            "AccountNumber",
            "Account_Number",
            "account_number",
            "Account No",
            "AccountNo"
        ]),

        # ----------------------------------------------------
        # DEVICE
        # ----------------------------------------------------

        "device_type": resolve([
            "DeviceType",
            "Device_Type",
            "device_type",
            "Device"
        ]),

        # ----------------------------------------------------
        # IP
        # ----------------------------------------------------

        "ip_address": resolve([
            "IPAddress",
            "IP_Address",
            "ip_address",
            "IP"
        ]),

        # ----------------------------------------------------
        # PREVIOUS AMOUNT
        # ----------------------------------------------------

        "previous_amount": resolve([
            "PreviousAmount",
            "Previous_Amount",
            "previous_amount",
            "previous amount"
        ]),

        # ----------------------------------------------------
        # TRANSACTION FREQUENCY
        # ----------------------------------------------------

        "transactions_last_24h": resolve([
            "TransactionsLast24Hours",
            "Transactions_Last_24h",
            "transactions_last_24h",
            "TransactionFrequency",
            "transaction_frequency",
            "TransactionsLast24h"
        ]),

        # ----------------------------------------------------
        # UNUSUAL LOCATION
        # ----------------------------------------------------

        "unusual_location": resolve([
            "UnusualLocation",
            "Unusual_Location",
            "unusual_location",
            "unusual location"
        ])
    }

    # --------------------------------------------------------
    # FRAUD LABEL COLUMNS
    # --------------------------------------------------------

    fraud_columns = [

        resolve(["fraud"]),
        resolve(["is_fraud"]),
        resolve(["fraud_flag"]),
        resolve(["fraudulent"]),
        resolve(["label"]),
        resolve(["class"]),
        resolve(["target"]),
        resolve(["isfraud"]),
        resolve(["fraud_label"]),
        resolve(["fraud_status"]),
        resolve(["FraudStatus"])
    ]

    resolved["fraud_label_columns"] = [
        column
        for column in fraud_columns
        if column is not None
    ]

    return lookup, resolved


# ============================================================
# FAST ROW VALUE
# ============================================================

def fast_value(row, column, default=None):

    if column is None:
        return default

    try:
        value = row.get(column, default)
    except AttributeError:
        return default

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    if isinstance(value, str) and not value.strip():
        return default

    return value


# ============================================================
# FRAUD LABELS
# ============================================================

FRAUD_VALUES = {
    "1",
    "true",
    "yes",
    "y",
    "fraud",
    "fraudulent",
    "fraud detected",
    "fraudulent transaction",
    "high risk"
}

SAFE_VALUES = {
    "0",
    "false",
    "no",
    "n",
    "safe",
    "legitimate",
    "normal",
    "legitimate transaction",
    "low risk"
}


# ============================================================
# EXISTING FRAUD LABEL
# ============================================================

def get_existing_fraud_label(row, resolved):

    fraud_columns = resolved.get(
        "fraud_label_columns",
        []
    )

    for column in fraud_columns:

        value = row.get(column)

        if value is None:
            continue

        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass

        text = str(value).strip().lower()

        if text in FRAUD_VALUES:
            return "fraud"

        if text in SAFE_VALUES:
            return "safe"

    return None


# ============================================================
# FRAUD / RISK ENGINE
# ============================================================

def calculate_risk(row, resolved):

    score = 0
    reasons = []

    # ========================================================
    # AMOUNT
    # ========================================================

    amount = clean_number(
        fast_value(
            row,
            resolved.get("amount"),
            0
        )
    )

    if amount >= 100000:

        score += 45

        reasons.append(
            "Very high transaction amount"
        )

    elif amount >= 50000:

        score += 30

        reasons.append(
            "High transaction amount"
        )

    elif amount >= 25000:

        score += 15

        reasons.append(
            "Elevated transaction amount"
        )

    # ========================================================
    # PREVIOUS AMOUNT
    # ========================================================

    previous = clean_number(
        fast_value(
            row,
            resolved.get("previous_amount"),
            0
        )
    )

    if previous > 0 and amount >= previous * 5:

        score += 20

        reasons.append(
            "Transaction much larger than previous amount"
        )

    # ========================================================
    # TRANSACTION FREQUENCY
    # ========================================================

    frequency = clean_number(
        fast_value(
            row,
            resolved.get("transactions_last_24h"),
            0
        )
    )

    if frequency >= 20:

        score += 30

        reasons.append(
            "Unusually high transaction frequency"
        )

    elif frequency >= 10:

        score += 15

        reasons.append(
            "High transaction frequency"
        )

    # ========================================================
    # UNUSUAL LOCATION
    # ========================================================

    unusual = str(
        fast_value(
            row,
            resolved.get("unusual_location"),
            ""
        )
    ).strip().lower()

    if unusual in {"yes", "true", "1", "y"}:

        score += 30

        reasons.append(
            "Unusual transaction location"
        )

    # ========================================================
    # DEVICE
    # ========================================================

    device = str(
        fast_value(
            row,
            resolved.get("device_type"),
            ""
        )
    ).strip().lower()

    if any(
        value in device
        for value in (
            "unknown",
            "new",
            "unrecognized"
        )
    ):

        score += 15

        reasons.append(
            "Unrecognized device"
        )

    # ========================================================
    # LOCATION
    # ========================================================

    location = str(
        fast_value(
            row,
            resolved.get("location"),
            ""
        )
    ).strip().lower()

    if any(
        value in location
        for value in (
            "unknown",
            "foreign",
            "international"
        )
    ):

        score += 10

        reasons.append(
            "Unusual location information"
        )

    # ========================================================
    # PAYMENT
    # ========================================================

    payment = str(
        fast_value(
            row,
            resolved.get("payment_method"),
            ""
        )
    ).strip().lower()

    if any(
        value in payment
        for value in (
            "unknown",
            "unrecognized"
        )
    ):

        score += 10

        reasons.append(
            "Unrecognized payment method"
        )

    # ========================================================
    # CHANNEL
    # ========================================================

    channel = str(
        fast_value(
            row,
            resolved.get("app_channel"),
            ""
        )
    ).strip().lower()

    if any(
        value in channel
        for value in (
            "unknown",
            "unrecognized"
        )
    ):

        score += 10

        reasons.append(
            "Unrecognized transaction channel"
        )

    # ========================================================
    # FINAL CLASSIFICATION
    # ========================================================

    if score >= 60:

        prediction = "Fraud"
        risk = "High"
        status = "Fraud Detected"

        probability = max(
            70,
            min(
                99,
                10 + score
            )
        )

    elif score >= 30:

        prediction = "Risky"
        risk = "Medium"
        status = "Requires Attention"

        probability = max(
            40,
            min(
                69,
                10 + score
            )
        )

    else:

        prediction = "Safe"
        risk = "Low"
        status = "Legitimate"

        probability = min(
            39,
            max(
                2,
                10 + score
            )
        )

    if not reasons:

        reasons.append(
            "No significant fraud indicators detected"
        )

    details = "; ".join(reasons)

    return {
        "prediction": prediction,
        "risk_level": risk,
        "status": status,
        "fraud_probability": probability / 100,
        "fraud_probability_percent": float(probability),
        "details": details,
        "fraud_reason": details,
        "risk_reason": details
    }


# ============================================================
# APPLY ANALYSIS
# ============================================================

def _apply_analysis(transaction, analysis):

    transaction.update(analysis)

    transaction["Prediction"] = (
        transaction["prediction"]
    )

    transaction["FraudProbability"] = (
        transaction["fraud_probability_percent"]
    )

    transaction["RiskLevel"] = (
        transaction["risk_level"]
    )

    transaction["Status"] = (
        transaction["status"]
    )

    return transaction


# ============================================================
# NORMALIZE TRANSACTION
# ============================================================

def normalize_transaction(
    row,
    lookup,
    resolved,
    index
):

    # IMPORTANT:
    # Keep original CSV fields so existing UI/details pages
    # continue to work.

    transaction = dict(row)

    # ========================================================
    # ID
    # ========================================================

    transaction_id = fast_value(
        row,
        resolved.get("id"),
        f"TXN{index + 1:08d}"
    )

    transaction_id = str(
        transaction_id
    ).strip()

    if not transaction_id:
        transaction_id = (
            f"TXN{index + 1:08d}"
        )

    transaction["transaction_id"] = transaction_id
    transaction["id"] = transaction_id

    # ========================================================
    # CUSTOMER
    # ========================================================

    customer = fast_value(
        row,
        resolved.get("customer_name"),
        "Unknown"
    )

    customer_text = str(customer).strip()

    if not customer_text:
        customer_text = "Unknown"

    transaction["customer_name"] = customer_text

    # ========================================================
    # AMOUNT
    # ========================================================

    transaction["amount"] = clean_number(
        fast_value(
            row,
            resolved.get("amount"),
            0
        )
    )

    # ========================================================
    # TEXT FIELDS
    # ========================================================

    text_fields = {
        "payment_method":
            resolved.get("payment_method"),

        "app_channel":
            resolved.get("app_channel"),

        "merchant":
            resolved.get("merchant"),

        "transaction_type":
            resolved.get("transaction_type"),

        "location":
            resolved.get("location"),

        "time":
            resolved.get("time"),

        "bank_name":
            resolved.get("bank_name"),

        "account_type":
            resolved.get("account_type"),

        "account_number":
            resolved.get("account_number"),

        "device_type":
            resolved.get("device_type"),

        "ip_address":
            resolved.get("ip_address"),

        "unusual_location":
            resolved.get("unusual_location")
    }

    for output_name, column in text_fields.items():

        value = fast_value(
            row,
            column,
            "-"
        )

        transaction[output_name] = str(value)

    # ========================================================
    # NUMERIC FIELDS
    # ========================================================

    transaction["previous_amount"] = clean_number(
        fast_value(
            row,
            resolved.get("previous_amount"),
            0
        )
    )

    transaction["transactions_last_24h"] = clean_number(
        fast_value(
            row,
            resolved.get("transactions_last_24h"),
            0
        )
    )

    # ========================================================
    # COMPATIBILITY ALIASES
    # ========================================================

    transaction["payment_type"] = (
        transaction["payment_method"]
    )

    transaction["channel"] = (
        transaction["app_channel"]
    )

    transaction["type"] = (
        transaction["transaction_type"]
    )

    transaction["city"] = (
        transaction["location"]
    )

    transaction["transaction_datetime"] = (
        transaction["time"]
    )

    transaction["company_merchant"] = (
        transaction["merchant"]
    )

    return transaction


# ============================================================
# PROGRESS CALLBACK
# ============================================================

def safe_progress_callback(
    callback,
    progress,
    processed,
    total,
    stage
):

    if callback is None:
        return

    try:

        callback(
            int(
                max(
                    0,
                    min(
                        100,
                        progress
                    )
                )
            ),
            int(processed),
            int(total),
            str(stage)
        )

    except Exception as error:

        print(
            "Progress callback warning:",
            repr(error)
        )


# ============================================================
# LARGE CSV PROCESSOR
# ============================================================

def process_csv(
    filepath,
    progress_callback=None
):

    if not filepath:
        raise ValueError(
            "No CSV file was provided."
        )

    filepath = os.fspath(filepath)

    if not os.path.isfile(filepath):

        raise FileNotFoundError(
            f"CSV file not found: {filepath}"
        )

    # ========================================================
    # FILE SIZE / ROW COUNT
    # ========================================================

    total_rows = 0

    try:

        with open(
            filepath,
            "rb"
        ) as csv_file:

            for block in iter(
                lambda: csv_file.read(4 * 1024 * 1024),
                b""
            ):

                total_rows += block.count(b"\n")

        if total_rows > 0:
            total_rows -= 1

    except Exception:

        total_rows = 0

    if total_rows <= 0:

        raise ValueError(
            "CSV file is empty."
        )

    safe_progress_callback(
        progress_callback,
        3,
        0,
        total_rows,
        "Opening transaction dataset..."
    )

    # ========================================================
    # CHUNK SIZE
    #
    # 10k is good for 30k/50k files without creating huge
    # temporary objects.
    # ========================================================

    CHUNK_SIZE = 10000

    transactions = []

    append_transaction = transactions.append

    processed_total = 0

    resolved = None
    lookup = None

    # ========================================================
    # READ CSV
    # ========================================================

    try:

        chunk_iterator = pd.read_csv(
            filepath,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="utf-8-sig"
        )

    except UnicodeDecodeError:

        chunk_iterator = pd.read_csv(
            filepath,
            chunksize=CHUNK_SIZE,
            low_memory=False,
            encoding="latin-1"
        )

    except Exception as error:

        raise ValueError(
            f"Unable to read CSV: {error}"
        )

    first_chunk = True

    # ========================================================
    # CHUNK LOOP
    # ========================================================

    try:

        for df_chunk in chunk_iterator:

            if df_chunk is None or df_chunk.empty:
                continue

            # =================================================
            # RESOLVE COLUMNS ONLY ONCE
            # =================================================

            if first_chunk:

                lookup, resolved = (
                    build_resolved_lookup(
                        df_chunk.columns
                    )
                )

                if resolved.get("amount") is None:

                    raise ValueError(
                        "CSV must contain an Amount, "
                        "Amount_INR or TransactionAmount "
                        "column."
                    )

                first_chunk = False

                safe_progress_callback(
                    progress_callback,
                    7,
                    0,
                    total_rows,
                    "CSV loaded. Preparing transaction columns..."
                )

            # =================================================
            # LOCAL REFERENCES
            # =================================================

            fraud_columns = (
                resolved.get(
                    "fraud_label_columns",
                    []
                )
            )

            # =================================================
            # USE ITertuples FOR LOWER OVERHEAD
            #
            # Convert column names once and create dictionaries
            # only for transactions that are actually returned.
            # =================================================

            columns = list(
                df_chunk.columns
            )

            # =================================================
            # ROW PROCESSING
            # =================================================

            for values in df_chunk.itertuples(
                index=False,
                name=None
            ):

                row = dict(
                    zip(
                        columns,
                        values
                    )
                )

                transaction = normalize_transaction(
                    row,
                    lookup,
                    resolved,
                    processed_total
                )

                # =================================================
                # EXISTING FRAUD LABEL
                # =================================================

                existing_label = None

                if fraud_columns:

                    for column in fraud_columns:

                        value = row.get(
                            column
                        )

                        if value is None:
                            continue

                        try:

                            if pd.isna(value):
                                continue

                        except (
                            TypeError,
                            ValueError
                        ):
                            pass

                        text = (
                            str(value)
                            .strip()
                            .lower()
                        )

                        if text in FRAUD_VALUES:

                            existing_label = "fraud"
                            break

                        if text in SAFE_VALUES:

                            existing_label = "safe"
                            break

                # =================================================
                # EXPLICIT FRAUD
                # =================================================

                if existing_label == "fraud":

                    details = (
                        "CSV fraud label indicates "
                        "this transaction is fraudulent."
                    )

                    analysis = {

                        "prediction":
                            "Fraud",

                        "risk_level":
                            "High",

                        "status":
                            "Fraud Detected",

                        "fraud_probability":
                            0.95,

                        "fraud_probability_percent":
                            95.0,

                        "details":
                            details,

                        "fraud_reason":
                            details,

                        "risk_reason":
                            details

                    }

                # =================================================
                # EXPLICIT SAFE
                # =================================================

                elif existing_label == "safe":

                    details = (
                        "CSV fraud label indicates "
                        "this transaction is legitimate."
                    )

                    analysis = {

                        "prediction":
                            "Safe",

                        "risk_level":
                            "Low",

                        "status":
                            "Legitimate",

                        "fraud_probability":
                            0.05,

                        "fraud_probability_percent":
                            5.0,

                        "details":
                            details,

                        "fraud_reason":
                            details,

                        "risk_reason":
                            details

                    }

                # =================================================
                # RISK ENGINE
                # =================================================

                else:

                    analysis = calculate_risk(
                        row,
                        resolved
                    )

                # =================================================
                # APPLY
                # =================================================

                _apply_analysis(
                    transaction,
                    analysis
                )

                append_transaction(
                    transaction
                )

                processed_total += 1

            # =================================================
            # RELEASE CHUNK MEMORY
            # =================================================

            del df_chunk

            # =================================================
            # PROGRESS
            # =================================================

            ratio = (
                processed_total / total_rows
                if total_rows > 0
                else 0
            )

            progress = (
                7 +
                int(
                    min(
                        0.85,
                        ratio * 0.85
                    ) * 100
                )
            )

            safe_progress_callback(
                progress_callback,
                progress,
                processed_total,
                total_rows,
                (
                    "Analyzing transactions... "
                    f"{processed_total:,} / "
                    f"{total_rows:,}"
                )
            )

    except Exception:

        # Do not leave large temporary objects alive.
        try:
            del chunk_iterator
        except Exception:
            pass

        raise

    # ========================================================
    # NO DATA
    # ========================================================

    if not transactions:

        raise ValueError(
            "CSV file contains no transaction records."
        )

    # ========================================================
    # FINAL PROGRESS
    # ========================================================

    safe_progress_callback(
        progress_callback,
        94,
        processed_total,
        total_rows,
        "Transaction analysis completed. Preparing results..."
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "transactions": transactions,
        "total": len(transactions)
    }


# ============================================================
# SINGLE TRANSACTION
# ============================================================

def predict_single_transaction(amount):

    amount = clean_number(amount)

    row = {
        "Amount": amount
    }

    resolved = {

        "amount":
            "Amount",

        "previous_amount":
            None,

        "transactions_last_24h":
            None,

        "unusual_location":
            None,

        "device_type":
            None,

        "location":
            None,

        "payment_method":
            None,

        "app_channel":
            None,

        "fraud_label_columns":
            [],

        "id":
            None,

        "customer_name":
            None,

        "merchant":
            None,

        "transaction_type":
            None,

        "time":
            None,

        "bank_name":
            None,

        "account_type":
            None,

        "account_number":
            None,

        "ip_address":
            None
    }

    return calculate_risk(
        row,
        resolved
    )


# ============================================================
# MAIN PREDICTION ENTRY POINT
# ============================================================

def predict_transaction(
    amount_or_file,
    progress_callback=None
):

    # ========================================================
    # CSV MODE
    # ========================================================

    if (
        isinstance(
            amount_or_file,
            (
                str,
                os.PathLike
            )
        )
        and os.path.isfile(
            amount_or_file
        )
    ):

        return process_csv(
            os.fspath(
                amount_or_file
            ),
            progress_callback=progress_callback
        )

    # ========================================================
    # SINGLE AMOUNT MODE
    # ========================================================

    return predict_single_transaction(
        amount_or_file
    )