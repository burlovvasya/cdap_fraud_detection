import pandas as pd

def load_data(path):
    return pd.read_csv(path)

def remove_duplicates(df):
    return df.drop_duplicates()

if name == "main":
    print("Fraud preprocessing module")
