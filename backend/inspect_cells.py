import zipfile, re

tmpl_path = r'C:\Users\Barusu\Documents\CoAutomate\backend\templates_excel\template_1_15.xlsx'
with zipfile.ZipFile(tmpl_path, 'r') as z:
    sheet2 = z.read('xl/worksheets/sheet2.xml').decode('utf-8')
    shared = z.read('xl/sharedStrings.xml').decode('utf-8')

# Show RAW XML for the rows we care about
for rn in [5, 6, 7, 8, 31, 37]:
    pat = r'<row[^>]*r="%d"[^>]*>.*?</row>' % rn
    rows = re.findall(pat, sheet2, re.DOTALL)
    if rows:
        print(f"--- RAW ROW {rn} ---")
        print(rows[0])
        print()
    else:
        print(f"--- ROW {rn} NOT FOUND ---\n")

# Also show drawing rels for sheet2 to understand signature location
tmpl_path2 = r'C:\Users\Barusu\Documents\CoAutomate\backend\templates_excel\template_1_15.xlsx'
with zipfile.ZipFile(tmpl_path2, 'r') as z:
    if 'xl/worksheets/_rels/sheet2.xml.rels' in z.namelist():
        print("--- SHEET2 RELS ---")
        print(z.read('xl/worksheets/_rels/sheet2.xml.rels').decode('utf-8'))
    if 'xl/drawings/drawing1.xml' in z.namelist():
        print("--- DRAWING1 ---")
        print(z.read('xl/drawings/drawing1.xml').decode('utf-8')[:800])
