import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    confusion_matrix
)


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# ============================================================
# DATASET PATH
# ============================================================

DATASET_PATH = os.path.join(
    BASE_DIR,
    "dataset",
    "creditcard.csv"
)


# ============================================================
# MODEL DIRECTORY
# ============================================================

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)


os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ============================================================
# MODEL FILE PATHS
# ============================================================

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "fraud_model.pkl"
)


SCALER_PATH = os.path.join(
    MODEL_DIR,
    "scaler.pkl"
)


FEATURE_PATH = os.path.join(
    MODEL_DIR,
    "feature_columns.pkl"
)


# ============================================================
# 1. CHECK DATASET
# ============================================================

print()
print("=" * 70)
print("AI FRAUD DETECTION - MODEL TRAINING")
print("=" * 70)


print()
print("Checking dataset...")


if not os.path.exists(
    DATASET_PATH
):

    raise FileNotFoundError(
        f"Dataset not found:\n{DATASET_PATH}"
    )


print(
    "Dataset found:",
    DATASET_PATH
)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print()
print("Loading dataset...")


df = pd.read_csv(
    DATASET_PATH
)


print(
    "Dataset loaded successfully."
)


print(
    "Dataset shape:",
    df.shape
)


print(
    "Number of rows:",
    len(df)
)


print(
    "Number of columns:",
    len(df.columns)
)


# ============================================================
# 3. CHECK REQUIRED TARGET COLUMN
# ============================================================

if "Class" not in df.columns:

    raise ValueError(
        "Dataset must contain a 'Class' column."
    )


# ============================================================
# 4. REMOVE COMPLETELY EMPTY ROWS
# ============================================================

df = df.dropna(
    how="all"
).reset_index(
    drop=True
)


print()
print(
    "Dataset shape after removing "
    "completely empty rows:",
    df.shape
)


# ============================================================
# 5. SEPARATE FEATURES AND TARGET
# ============================================================

print()
print("Preparing features and target...")


X = df.drop(
    "Class",
    axis=1
).copy()


y = df["Class"].copy()


# ============================================================
# 6. CHECK FEATURE COLUMNS
# ============================================================

feature_columns = list(
    X.columns
)


print()
print(
    "AI MODEL FEATURES:"
)


for number, column in enumerate(
    feature_columns,
    start=1
):

    print(
        f"{number:02d}. {column}"
    )


print()
print(
    "Total AI features:",
    len(feature_columns)
)


# ============================================================
# 7. CHECK EXPECTED CREDIT CARD DATASET
# ============================================================

expected_features = [

    "Time",

    "V1",
    "V2",
    "V3",
    "V4",
    "V5",
    "V6",
    "V7",
    "V8",
    "V9",
    "V10",
    "V11",
    "V12",
    "V13",
    "V14",
    "V15",
    "V16",
    "V17",
    "V18",
    "V19",
    "V20",
    "V21",
    "V22",
    "V23",
    "V24",
    "V25",
    "V26",
    "V27",
    "V28",

    "Amount"
]


missing_features = [

    column

    for column in expected_features

    if column not in feature_columns
]


if missing_features:

    raise ValueError(

        "The creditcard.csv dataset is missing "
        "required features:\n"

        + ", ".join(
            missing_features
        )
    )


# ============================================================
# 8. CONVERT FEATURES TO NUMERIC
# ============================================================

print()
print(
    "Converting feature columns to numeric..."
)


for column in feature_columns:

    X[column] = pd.to_numeric(
        X[column],
        errors="coerce"
    )


# ============================================================
# 9. HANDLE MISSING VALUES
# ============================================================

missing_before = int(
    X.isna().sum().sum()
)


print(
    "Missing feature values before cleaning:",
    missing_before
)


if missing_before > 0:

    print(
        "Replacing missing values with column medians..."
    )


    for column in feature_columns:

        median_value = X[column].median()


        if pd.isna(
            median_value
        ):

            median_value = 0


        X[column] = X[column].fillna(
            median_value
        )


missing_after = int(
    X.isna().sum().sum()
)


print(
    "Missing feature values after cleaning:",
    missing_after
)


# ============================================================
# 10. CLEAN TARGET
# ============================================================

y = pd.to_numeric(
    y,
    errors="coerce"
)


# Remove rows where Class is invalid

valid_target_rows = y.notna()


X = X.loc[
    valid_target_rows
].reset_index(
    drop=True
)


y = y.loc[
    valid_target_rows
].reset_index(
    drop=True
)


# Convert target to integer

y = y.astype(int)


# ============================================================
# 11. DISPLAY CLASS DISTRIBUTION
# ============================================================

print()
print(
    "Fraud class distribution:"
)


print(
    y.value_counts()
)


if y.nunique() < 2:

    raise ValueError(
        "The dataset must contain at least "
        "two target classes."
    )


# ============================================================
# 12. SCALE ONLY THE AMOUNT COLUMN
# ============================================================
#
# The original project trained the model by scaling Amount.
#
# Time and V1-V28 remain unchanged.
#
# This is important because predict.py will use the same
# scaler when processing uploaded transactions.
#
# ============================================================

print()
print(
    "Scaling Amount column..."
)


scaler = StandardScaler()


X["Amount"] = scaler.fit_transform(
    X[["Amount"]]
)


print(
    "Amount scaling completed."
)


# ============================================================
# 13. TRAIN / TEST SPLIT
# ============================================================

print()
print(
    "Splitting dataset into training and testing data..."
)


X_train, X_test, y_train, y_test = train_test_split(

    X,

    y,

    test_size=0.20,

    random_state=42,

    stratify=y
)


print(
    "Training rows:",
    len(X_train)
)


print(
    "Testing rows:",
    len(X_test)
)


# ============================================================
# 14. CREATE RANDOM FOREST MODEL
# ============================================================

print()
print(
    "Creating Random Forest model..."
)


model = RandomForestClassifier(

    n_estimators=100,

    random_state=42,

    class_weight="balanced",

    n_jobs=-1
)


# ============================================================
# 15. TRAIN MODEL
# ============================================================

print()
print(
    "Training Random Forest model..."
)

print(
    "Please wait..."
)


model.fit(
    X_train,
    y_train
)


print()
print(
    "Model training completed successfully."
)


# ============================================================
# 16. TEST MODEL
# ============================================================

print()
print(
    "Testing model..."
)


y_pred = model.predict(
    X_test
)


# ============================================================
# 17. ACCURACY
# ============================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)


print()
print(
    "=" * 70
)


print(
    "MODEL PERFORMANCE"
)


print(
    "=" * 70
)


print(
    "Accuracy:",
    round(
        accuracy * 100,
        2
    ),
    "%"
)


# ============================================================
# 18. CLASSIFICATION REPORT
# ============================================================

print()
print(
    "Classification Report:"
)


print(
    classification_report(
        y_test,
        y_pred,
        zero_division=0
    )
)


# ============================================================
# 19. CONFUSION MATRIX
# ============================================================

print()
print(
    "Confusion Matrix:"
)


print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# ============================================================
# 20. SAVE RANDOM FOREST MODEL
# ============================================================

print()
print(
    "Saving Random Forest model..."
)


joblib.dump(
    model,
    MODEL_PATH
)


print(
    "Model saved:"
)


print(
    MODEL_PATH
)


# ============================================================
# 21. SAVE SCALER
# ============================================================

print()
print(
    "Saving Amount scaler..."
)


joblib.dump(
    scaler,
    SCALER_PATH
)


print(
    "Scaler saved:"
)


print(
    SCALER_PATH
)


# ============================================================
# 22. SAVE FEATURE COLUMNS
# ============================================================
#
# THIS FIXES YOUR CURRENT ERROR:
#
# FileNotFoundError:
# models\\feature_columns.pkl
#
# ============================================================

print()
print(
    "Saving feature columns..."
)


joblib.dump(
    feature_columns,
    FEATURE_PATH
)


print(
    "Feature columns saved:"
)


print(
    FEATURE_PATH
)


# ============================================================
# 23. VERIFY SAVED FILES
# ============================================================

print()
print(
    "=" * 70
)


print(
    "VERIFYING MODEL FILES"
)


print(
    "=" * 70
)


files_to_check = [

    (
        "Random Forest model",
        MODEL_PATH
    ),

    (
        "Scaler",
        SCALER_PATH
    ),

    (
        "Feature columns",
        FEATURE_PATH
    )
]


all_files_exist = True


for name, path in files_to_check:

    if os.path.exists(path):

        file_size = os.path.getsize(
            path
        )


        print(
            f"[OK] {name}"
        )


        print(
            f"     {path}"
        )


        print(
            f"     Size: {file_size:,} bytes"
        )


    else:

        print(
            f"[ERROR] {name} NOT FOUND"
        )


        all_files_exist = False


# ============================================================
# 24. FINAL VERIFICATION
# ============================================================

print()
print(
    "=" * 70
)


if all_files_exist:

    print(
        "MODEL SETUP COMPLETED SUCCESSFULLY!"
    )

    print()
    print(
        "Created files:"
    )

    print(
        "1. models/fraud_model.pkl"
    )

    print(
        "2. models/scaler.pkl"
    )

    print(
        "3. models/feature_columns.pkl"
    )

    print()
    print(
        "Number of model input features:",
        len(feature_columns)
    )


else:

    print(
        "ERROR: One or more model files "
        "could not be created."
    )


print(
    "=" * 70
)


print()
print(
    "Training process finished."
)