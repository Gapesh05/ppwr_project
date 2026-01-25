import pandas as pd
p = r'c:\PPWR\New folder\PFAS_V0.2\Helper_Data\Packaging BOM 1 for Automation.xlsx'
print('Reading:', p)
df = pd.read_excel(p, sheet_name=0, dtype=str)
cols = [str(c).strip().replace('\n','').replace('\r','').replace(' ', '_').lower() for c in df.columns]
print('Normalized columns:')
print(cols)
print('\nFirst 5 rows sample:')
print(df.head(5).to_dict(orient='records'))
