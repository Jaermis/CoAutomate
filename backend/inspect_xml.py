import zipfile, re

# Map openpyxl cell refs to ACTUAL cell refs in the sheet XML (due to merged cells)
# Also check where B6, B7, I37, A31 actually live
with zipfile.ZipFile(r'C:\Users\Barusu\Documents\CoAutomate\backend\templates_excel\template_1_15.xlsx', 'r') as z:
    sheet = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
    shared = z.read('xl/sharedStrings.xml').decode('utf-8')

# Find all cells in rows 5,6,7,8,37,31 
for row_num in [5, 6, 7, 8, 31, 37]:
    pat = r'<row[^>]*r="%d"[^>]*>.*?</row>' % row_num
    rows = re.findall(pat, sheet, re.DOTALL)
    if rows:
        print('ROW %d:' % row_num, rows[0][:500])
    print()

# Show shared strings that are our data
si_blocks = re.findall(r'<si>.*?</si>', shared, re.DOTALL)
for check_idx in [2, 6, 9, 17, 18, 19]:
    if check_idx < len(si_blocks):
        print('ss[%d]:' % check_idx, si_blocks[check_idx][:100])
