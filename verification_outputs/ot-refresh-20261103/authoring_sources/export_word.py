from pathlib import Path
import sys,json,re
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
r=Path(sys.argv[1]);head=sys.argv[2];out=Path(sys.argv[3]);out.mkdir(exist_ok=True)
def setup(d,title):
 s=d.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7)
 s.top_margin=Cm(1.8);s.bottom_margin=Cm(1.8);s.left_margin=Cm(2);s.right_margin=Cm(2)
 for n,size in [('Normal',10.5),('Title',21),('Heading 1',15),('Heading 2',12),('Heading 3',11)]:
  st=d.styles[n];st.font.name='Times New Roman';st.font.size=Pt(size);st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Songti SC' if n=='Normal' else 'PingFang SC')
  st.paragraph_format.space_after=Pt(6)
  if n!='Normal':st.font.color.rgb=RGBColor.from_string('17365D')
 d.styles['Normal'].paragraph_format.line_spacing=1.15
 f=s.footer.paragraphs[0];f.alignment=2;f.add_run('FlowA · 第六轮研究记录  |  ');a=OxmlElement('w:fldSimple');a.set(qn('w:instr'),'PAGE');f._p.append(a)
 d.core_properties.author='';d.core_properties.title=title

def clean(s):
 s=re.sub(r'\[([^]]+)\]\(([^)]+)\)',lambda m:m[1]+'（'+m[2]+'）',s)
 return s.replace('**','').replace('`','')

def addmd(d,s):
 lines=s.splitlines();i=0
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('|') and i+1<len(lines) and re.match(r'^\|[-: |]+\|$',lines[i+1].strip()):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    raw=lines[i].strip();i+=1
    if re.match(r'^\|[-: |]+\|$',raw):continue
    rows.append([clean(x.strip()) for x in raw.strip('|').split('|')])
   tab=d.add_table(rows=0,cols=len(rows[0]));tab.style='Light Shading Accent 1'
   for row in rows:
    cells=tab.add_row().cells
    for c,txt in zip(cells,row):
     c.text=txt
     for p in c.paragraphs:
      for a in p.runs:a.font.size=Pt(8.5)
    trpr=tab.rows[-1]._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
   d.add_paragraph();continue
  if line.startswith('#'):
   level=min(len(line)-len(line.lstrip('#')),3)
   d.add_heading(clean(line.lstrip('#').strip()),max(1,level-1))
  elif line.startswith('>'):d.add_paragraph(clean(line.lstrip('> ').strip()),style='Quote')
  else:d.add_paragraph(clean(line))
  i+=1

w=Document();setup(w,'FlowA 原创贡献攻关备忘录·第六轮')
w.add_heading('FlowA 原创贡献攻关备忘录',0)
w.add_paragraph('第六轮｜2026年11月3日｜中文研究记录')
w.add_paragraph('结论：完成了可核对的机制分析，但主要原创贡献仍未成立。核心矩缺口与经典最优输运成本差精确等价，已降级为机制引理，不作为新采样方法宣传。')
w.add_paragraph('本轮完成：四个条件命题及证明、100个CPU解析检查、近似路径反例、原始文献对照与45项自查记录更新。新增GPU用量为0。')
w.add_paragraph('下一研究门槛：在实际神经流上找到可观测、可预测并能接受独立干预检验的耦合失配；原有CIFAR负结果继续保留。不能用合成检查替代独立生成质量验证。')
w.add_paragraph('对应GitHub与Mac提交：'+head)
w.add_paragraph('本文件是原创性研究备忘录及证明记录，不是新增正结果的投稿定稿。中文v6主结果未改写。')
w.add_page_break()
source=(r/'docs/audit/manuscript-originality-round6-2026-11-03.md').read_text().split('\n',1)[1]
addmd(w,source)
w.save(out/'FlowA_原创贡献攻关备忘录_第六轮.docx')

z=json.loads((r/'docs/audit/manuscript-selfcheck-2026-11-02.json').read_text());d=Document();setup(d,'FlowA 投稿改进自查表·第六轮')
d.add_heading('FlowA 投稿改进自查表',0);d.add_paragraph('第六轮｜2026年11月3日｜完整45项')
d.add_paragraph('对应GitHub与Mac提交：'+head)
d.add_paragraph('本轮重点为SC-04/05原创贡献。机制证明与100个CPU检查已完成，但核心障碍命题因与经典输运成本差等价而降为引理；原创性条目继续保留证据缺口。')
counts={k:sum(x['status']==k for x in z['items']) for k in z['status_rules']}
d.add_paragraph('当前状态：'+'；'.join(k+' '+str(v) for k,v in counts.items())+'。VERIFIED只代表条目限定核查范围。')
d.add_heading('状态定义',1)
for k,v in z['status_rules'].items():d.add_paragraph(k+'：'+v)
d.add_heading('历轮重要更正',1)
for x in z['corrections']:d.add_paragraph(x,style='List Bullet')
group=None
for x in z['items']:
 if group!=x['group']:group=x['group'];d.add_heading(group,1)
 d.add_heading(x['id']+' '+x['reviewer_question'],2)
 for k,label in [('priority','优先级'),('status','状态'),('acceptance','验收'),('finding','当前发现'),('next_action','下一步'),('verification_scope','验证范围')]:
  if x.get(k):d.add_paragraph(label+'：'+x[k])
 d.add_paragraph('证据入口：'+'；'.join(x['evidence']))
d.add_heading('历史与同步',1);d.add_paragraph('全部45项及逐轮历史原文保存在项目同名JSON与Markdown记录中。Word列出完整45项的最新状态与证据；历史记录不被覆盖。服务器与Mac复核范围、摘要及耗时见本轮交付收据。')
d.save(out/'FlowA_投稿改进自查表_第六轮更新.docx')
print('Word documents created')
