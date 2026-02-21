import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

def load_data(path):
    return pd.read_csv(path)

def remove_duplicates(df):
    logging.info("Removing duplicates")
    return df.drop_duplicates()

if name == "main":
    print("!!!Fraud Detection Preprocessing!!!")



