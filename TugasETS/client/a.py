import pandas as pd


data = pd.read_csv('report_thread.csv')
data.to_excel('report_thread.xlsx', index=False)