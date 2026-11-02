from pathlib import Path
import json,sys
from docx import Document
from docx.shared import Pt,Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
repo=Path(sys.argv[1]);out=Path(sys.argv[2]);d=json.loads((repo/'docs/audit/manuscript-selfcheck-2026-11-02.json').read_text())
w=Document();s=w.sections[0];s.top_margin=Cm(1.8);s.bottom_margin=Cm(1.8)
for n in ['Normal','Heading 1','Heading 2','Title']:
 st=w.styles[n];st.font.name='Times New Roman';st.font.size=Pt(10.5 if n=='Normal' else 14);st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'STSong')
w.add_heading('FlowA 投稿改进自查表',0)
w.add_paragraph('2026-11-03｜45 项｜与 GitHub 项目记录一致')
w.add_paragraph('本表完整记录上一轮审稿视角的改进计划。“已登记”不等于问题已解决；“已定位证据”不等于独立验收通过。先查源码、实际配置和已有记录，避免重复安排已经完成的实验。')
w.add_paragraph('对应项目提交：'+sys.argv[3])
w.add_heading('第五轮结果与优先处理',1)
a=json.loads((repo/'verification_outputs/cifar-study-20261103/REPORT.json').read_text())
b=json.loads((repo/'verification_outputs/cifar-consistent-candidate-20261103/REPORT.json').read_text())
gpu=json.loads((repo/'verification_outputs/cifar-study-20261103/GLOBAL_BUDGET_FINAL.json').read_text())
full=next(x for x in a['primary_contrasts'] if x['arm']=='full_euler' and x['baseline']=='baseline_euler')
w.add_paragraph(f"五臂独立CIFAR研究完整完成12单元/60臂结果。完整配置减Euler的KID成本面积差{full['mean']:+.6f}（越低越好），不支持迁移优势；零时间四轮候选退化更大。")
if b['status']=='COMPLETE':
 for c in b['primary_contrasts']:
  w.add_paragraph(f"两轮后段时间匹配候选减{c['baseline']}：两点KID面积差{c['mean']:+.6f}，名义95%区间{c['nominal_ci95']}，两比较Holm p={c['holm_p']:.4g}；达到预定改善条件：{c['clears_preregistered_practical_improvement']}。")
else:w.add_paragraph('两轮候选因资源条件未启动；不报告其质量结论。')
w.add_paragraph(f"保守GPU作业墙钟累计{gpu['conservatively_accounted_total_s']}秒 / 上限7200秒；未购买资源，本协议不再启动GPU作业。")
for v in [
 'P0 原创定位：端点构造与Diamond Maps/NR-SMC等存在直接相关操作。先识别独立且有价值的可检验贡献；没有时不按新采样方法匆忙投稿。',
 'P0 外部确认：当前独立模型的原完整配置为不利结果；候选即使局部改善，也不等于新训练重复或完整前沿。后续设计应服务可辨贡献，不能补种子挑显著性。',
 'P1 理论与评价：保留训练耦合反例、时间对应和批相关KID范围；经典恒等式与工程完整性不代替新颖性或质量机制。',
 'P1 投稿口径：官方2026起停止更新中科院分区表；按2025历史大类/小类及单位规则核对。TNNLS仅为主题候选，正式英文双栏与最新作者须知尚未完成验收。']:
 w.add_paragraph(v,style='List Bullet')
w.add_paragraph('本轮判断：证据更完整，但不足以称“硬中科院一区稿”。下一步不应是增加背景篇幅或把缺口改为通过。')
w.add_heading('需要更正的先前判断',1)
for x in d['corrections']:w.add_paragraph(x,style='List Bullet')
w.add_heading('状态定义',1)
counts={k:sum(x['status']==k for x in d['items']) for k in d['status_rules']}
w.add_paragraph('当前状态：'+ '；'.join(k+' '+str(v) for k,v in counts.items())+'。VERIFIED仅指各项注明的源码、统计或稿件修正范围。')
for k,v in d['status_rules'].items():w.add_paragraph(k+'：'+v)
group=None
for r in d['items']:
 if group!=r['group']:
  group=r['group'];w.add_heading(group,1)
 w.add_heading(r['id']+'  '+r['reviewer_question'],2)
 w.add_paragraph('优先级：'+r['priority']+'　状态：'+r['status'])
 w.add_paragraph('验收标准：'+r['acceptance'])
 w.add_paragraph('证据入口：'+'；'.join(r['evidence']))
 if r.get('verification_scope'):w.add_paragraph('验证范围：'+r['verification_scope'])
 w.add_paragraph('本轮核查与修改：'+r['finding']) if r['finding'] else w.add_paragraph('核查结论 / 精确文件行号 / 未解决项：待填写。')
 if r.get('next_action'):w.add_paragraph('下一步：'+r['next_action'])
w.add_heading('同步与后续使用',1)
w.add_paragraph('权威记录：项目 docs/audit/manuscript-selfcheck-2026-11-02.json 及同名 Markdown。todo.json 已注册入口，audit 索引已更新。逐项完成时，应先更新仓库记录，再重新导出本表。')
w.add_paragraph('源码能确定实现、调用路径与指标计算；新颖性、因果解释、外部有效性和期刊判断仍需结合原始文献与实验设计，不能仅凭代码存在判定通过。')
f=s.footer.paragraphs[0];f.alignment=2;a=OxmlElement('w:fldSimple');a.set(qn('w:instr'),'PAGE');f._p.append(a)
w.core_properties.title='FlowA manuscript self-check';w.core_properties.author='';w.save(out);print(out)
