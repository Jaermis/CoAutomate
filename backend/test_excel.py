import sys, re, zipfile
sys.path.insert(0, '.')
from database import SessionLocal, User
from excel_service import generate_coa_report
from datetime import date

db = SessionLocal()
u = db.query(User).first()
print("User:", u.full_name, u.department, u.college, u.total_teaching_load, u.term_school_year)

path, info = generate_coa_report(u, date(2026, 6, 16))
print('Generated:', path.name, '  Size:', path.stat().st_size, 'bytes')

with zipfile.ZipFile(str(path), 'r') as z:
    sheet2 = z.read('xl/worksheets/sheet2.xml').decode('utf-8')
    shared = z.read('xl/sharedStrings.xml').decode('utf-8')

si_blocks = re.findall(r'<si>.*?</si>', shared, re.DOTALL)
def si_text(idx):
    if idx < len(si_blocks):
        return re.sub(r'<[^>]+>', '', si_blocks[idx]).strip()
    return '?'

# Verify all 8 cells
checks = ['B5','B6','B7','G8','J5','J6','A31','I37']
for cr in checks:
    # Try shared string
    pat_s = r'<c r="' + re.escape(cr) + r'"[^>]*t="s"[^>]*><v>(\d+)</v></c>'
    m_s = re.search(pat_s, sheet2)
    if m_s:
        idx = int(m_s.group(1))
        print(f"  {cr}: shared[{idx}] = {repr(si_text(idx))}")
        continue
    # Try numeric
    pat_n = r'<c r="' + re.escape(cr) + r'"[^>]*><v>([^<]+)</v></c>'
    m_n = re.search(pat_n, sheet2)
    if m_n:
        print(f"  {cr}: numeric = {m_n.group(1)}")
        continue
    print(f"  {cr}: NOT FOUND")

# Verify Wingdings preserved
styles = z.read('xl/styles.xml').decode('utf-8') if False else ''
with zipfile.ZipFile(str(path), 'r') as z:
    styles = z.read('xl/styles.xml').decode('utf-8')
    print()
    print('Wingdings 2 in styles:', 'Wingdings 2' in styles)
    print('charset val in styles:', 'charset val' in styles)

db.close()
print('\nDONE')
