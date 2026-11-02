from pathlib import Path
import re,sys
from docx import Document
from docx.shared import Pt,Cm,RGBColor, Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
repo=Path(sys.argv[1]);src=repo/'docs/drafts/paper-A-zh-reviewed-round5-2026-11-03.md';out=Path(sys.argv[2])
d=Document();s=d.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=Cm(2);s.bottom_margin=Cm(2);s.left_margin=Cm(2);s.right_margin=Cm(2)
for name,size in [('Normal',10.5),('Title',20),('Heading 1',14),('Heading 2',11.5),('Caption',9)]:
 st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'STSong');st.paragraph_format.space_after=Pt(6)
 if name in ['Title','Heading 1','Heading 2']:st.font.color.rgb=RGBColor.from_string('17365D')
lines=src.read_text().splitlines();i=0
while i<len(lines):
 line=lines[i].strip();i+=1
 if not line:continue
 if line.startswith('|'):
  rows=[line]
  while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
  values=[[x.strip() for x in r.strip('|').split('|')] for r in rows if not re.fullmatch(r'[|\s:\-]+',r)]
  tab=d.add_table(rows=1,cols=len(values[0]));tab.style='Light Shading Accent 1'
  for cell,val in zip(tab.rows[0].cells,values[0]):cell.text=val
  trp=tab.rows[0]._tr.get_or_add_trPr();trp.append(OxmlElement('w:tblHeader'))
  for row in values[1:]:
   for cell,val in zip(tab.add_row().cells,row):cell.text=val
  for row in tab.rows:
   row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
   for cell in row.cells:
    for para in cell.paragraphs:
     para.paragraph_format.keep_with_next=False
     for run in para.runs:run.font.size=Pt(9)
  for cell in tab.rows[0].cells:
   for para in cell.paragraphs:para.paragraph_format.keep_with_next=True
  d.add_paragraph().paragraph_format.keep_with_next=False;continue
 if line.startswith('!['):
  match=re.match(r'!\[(.*?)\]\((.*?)\)',line)
  picpath=(src.parent/match.group(2)).resolve()
  from PIL import Image
  with Image.open(picpath) as im: ratio=im.height/im.width
  width=min(6.6,7.7/ratio)
  d.add_picture(str(picpath),width=Inches(width))
  d.paragraphs[-1].paragraph_format.keep_with_next=True
  continue
 if line.startswith('# '):d.add_heading(line[2:],0)
 elif line.startswith('## '):d.add_heading(line[3:],1)
 elif line.startswith('### '):d.add_heading(line[4:],2)
 else:d.add_paragraph(line,style='Caption' if re.match(r'^(图 \d|表 [IVX]+\.)',line) else 'Normal')
f=s.footer.paragraphs[0];f.alignment=2;a=OxmlElement('w:fldSimple');a.set(qn('w:instr'),'PAGE');f._p.append(a)
d.core_properties.author='';d.core_properties.title='FlowA 中文修订稿 v6';d.core_properties.subject='Source-aligned revision; '+sys.argv[3];d.save(out)
print(out)
