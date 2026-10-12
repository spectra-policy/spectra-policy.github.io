"""Port selected paper passages into the CSP-style project page.

Requires PyMuPDF for authoring only. The source PDF is never modified or served.
Prose and source captions are extracted from recorded rectangles; only PDF line
wraps are normalized. Excerpts select complete original sentences without
rewriting them, apart from explicitly recorded citation-formatting corrections
and approved website text edits.
The manifest records both source passages and selections. Source captions remain
in the manifest for provenance but are not displayed beneath figures or tables.
"""
from pathlib import Path
import re, html, hashlib, json
import pymupdf as pdf

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'SPECTRA__Force_Gated_Spectral_Diffusionfor_Robot_Manipulation.pdf'
DOC=pdf.open(SOURCE)
SOURCE_HASH=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
CONTENT=[]

def clean(s):
    # Remove only hyphenation introduced by PDF line breaks, not compound hyphens.
    for a,b in [('ex-\ntraction','extraction'),('coef-\nficients','coefficients'),
                ('expecta-\ntion','expectation'),('docu-\nments','documents')]:
        s=s.replace(a,b)
    return ' '.join(re.sub(r'-\n\s*','-',s).split())

def extract(page,y0,y1):
    return clean(DOC[page-1].get_textbox(pdf.Rect(103,y0,510,y1)))

def paragraph(*rects, excerpts=None, citation_corrections=(), text_corrections=()):
    source_text=' '.join(extract(*r) for r in rects)
    text=source_text
    if excerpts:
        selected=[]
        for start,end in excerpts:
            first=source_text.index(start)
            last=source_text.index(end,first)+len(end)
            selected.append(source_text[first:last])
        text=' '.join(selected)
    for original,corrected in (*citation_corrections, *text_corrections):
        assert text.count(original)==1
        text=text.replace(original,corrected)
    entry={'type':'paragraph','source_rects':rects,
           'source_text':source_text,'excerpts':excerpts,'text':text}
    if citation_corrections:
        entry['citation_corrections']=citation_corrections
    if text_corrections:
        entry['text_corrections']=text_corrections
    CONTENT.append(entry)
    return '<p>'+html.escape(text)+'</p>\n'

def bullets(page,y0,y1):
    text=extract(page,y0,y1)
    items=[v.strip() for v in text.split('•') if v.strip()]
    CONTENT.append({'type':'list','source_rects':[(page,y0,y1)],'items':items})
    return '<ul>\n'+''.join('<li>'+html.escape(v)+'</li>\n' for v in items)+'</ul>\n'

def figure(name,page,rect,caption_bounds,alt=None):
    dest=ROOT/'site/static/media'/f'{name}.png'
    dest.parent.mkdir(parents=True,exist_ok=True)
    pix=DOC[page-1].get_pixmap(matrix=pdf.Matrix(3,3),clip=pdf.Rect(*rect),alpha=False)
    pix.save(dest)
    caption=extract(page,*caption_bounds)
    CONTENT.append({'type':'figure','page':page,'crop':rect,'caption_bounds':caption_bounds,
                    'file':str(dest.relative_to(ROOT)),'caption':caption})
    alt=alt or caption.split('. ')[0]
    return f'<figure><img src="static/media/{name}.png" width="{pix.width}" height="{pix.height}" alt="{html.escape(alt)}" loading="lazy" decoding="async"></figure>\n'

def section(key,title,body):
    return f'<section id="{key}" aria-labelledby="{key}-title">\n<h2 id="{key}-title">{title}</h2><hr>\n<div class="section-body">\n{body}</div>\n</section>\n'

def evaluation_block(key,title,body):
    return f'<div id="{key}" class="evaluation-block" role="group" aria-labelledby="{key}-title">\n<h3 id="{key}-title">{title}</h3>\n{body}</div>\n'

def simulation_table():
    source_file='scripts/simulation_table.json'
    data=json.loads((ROOT/source_file).read_text())
    rows=[row for group in data['groups'] for row in group['rows']]
    best=[max(float(row[i]) for row in rows) for i in range(2,8)]
    caption=extract(6,436,458)
    CONTENT.append({'type':'table','page':6,'source_rect':[108,209,505,433],
                    'source_file':source_file,'data':data,'caption':caption,
                    'caption_bounds':[436,458]})
    parts=['<figure class="simulation-table">',
           '<div class="table-scroll" role="region" aria-label="Simulation success rates, scroll horizontally on small screens" tabindex="0">',
           '<table class="results-table">',
           '<caption class="sr-only">Table 1: Policy architectures and simulation success rates (%)</caption>',
           '<colgroup span="2"></colgroup><colgroup span="4"></colgroup><colgroup span="2"></colgroup>',
           '<thead><tr><th scope="col" rowspan="2">Policy</th><th scope="col" rowspan="2">Space</th>',
           '<th scope="colgroup" colspan="4">ManiSkill</th><th scope="colgroup" colspan="2">MimicGen</th></tr><tr>']
    parts.extend('<th scope="col">'+html.escape(label).replace(' ','<br>')+'</th>' for label in data['columns'][2:])
    parts.append('</tr></thead>')
    for group in data['groups']:
        parts.append(f'<tbody class="{group["class"]}">')
        if len(group['rows'])>1:
            parts.append(f'<tr class="group-heading"><th scope="rowgroup" colspan="8">{html.escape(group["label"])}</th></tr>')
        for row in group['rows']:
            parts.append('<tr><th scope="row">'+html.escape(row[0])+'</th><td>'+html.escape(row[1])+'</td>')
            for i,value in enumerate(row[2:]):
                text=f'<strong>{value}</strong>' if float(value)==best[i] else value
                parts.append('<td>'+text+'</td>')
            parts.append('</tr>')
        parts.append('</tbody>')
    parts.append('</table></div></figure>')
    return '\n'.join(parts)+'\n'

def normalization_table():
    source_file='scripts/normalization_table.json'
    data=json.loads((ROOT/source_file).read_text())
    best=[max(float(row[i]) for row in data['rows']) for i in range(1,6)]
    CONTENT.append({'type':'table','page':7,'source_rect':[107,119,505,214],
                    'source_file':source_file,'data':data,'caption':extract(7,84,115),
                    'caption_bounds':[84,115]})
    parts=['<figure class="normalization-results">',
           '<div class="table-scroll" role="region" aria-label="Spectral normalization success rates, scroll horizontally on small screens" tabindex="0">',
           '<table class="results-table normalization-table">',
           '<caption class="sr-only">Effect of spectral signal-to-noise balancing: task success (%)</caption>',
           '<thead><tr>']
    parts.extend('<th scope="col">'+html.escape(label)+'</th>' for label in data['columns'])
    parts.append('</tr></thead><tbody>')
    for row in data['rows']:
        row_class=' class="normalization-variant"' if row[0].startswith('SPECTRA') else ''
        parts.append(f'<tr{row_class}><th scope="row">{html.escape(row[0])}</th>')
        for i,value in enumerate(row[1:]):
            text=f'<strong>{value}</strong>' if float(value)==best[i] else value
            parts.append('<td>'+text+'</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div></figure>')
    return '\n'.join(parts)+'\n'

def force_bandwidth_table():
    source_file='scripts/force_bandwidth_table.json'
    data=json.loads((ROOT/source_file).read_text())
    caption=extract(7,391,433)
    CONTENT.append({'type':'table','page':7,'source_rect':[108,259,504,380],
                    'source_file':source_file,'data':data,'caption':caption,
                    'caption_bounds':[391,433]})
    parts=['<figure class="force-bandwidth-table">',
           '<div class="table-scroll" role="region" aria-label="Force feedback and action bandwidth results, scroll horizontally on small screens" tabindex="0">',
           '<table class="results-table bandwidth-table">',
           '<caption class="sr-only">Force benefits depend on action bandwidth</caption>',
           '<colgroup span="1"></colgroup><colgroup span="2"></colgroup><colgroup span="2"></colgroup>',
           '<thead><tr><th scope="col" rowspan="2">Task</th>',
           '<th scope="colgroup" colspan="2">Low-frequency</th><th scope="colgroup" colspan="2">Full-spectrum</th></tr>',
           '<tr><th scope="col">No force → With force (%)</th><th scope="col">Gain (pp)</th>',
           '<th scope="col">No force → With force (%)</th><th scope="col">Gain (pp)</th></tr></thead><tbody>']
    for row in data['rows']:
        parts.append('<tr><th scope="row">'+html.escape(row['task'])+'</th>')
        for band in ('low','full'):
            before,after,gain=row[band]
            delta=float(gain)
            assert abs(float(after)-float(before)-delta)<1e-9
            assert abs(delta)<=15
            # Identical -15 to +15 pp scales for both columns; text is accessible,
            # while these decorative CSS bars preserve the paper's visual comparison.
            width=abs(delta)/30*100
            left=50-width if delta<0 else 50
            parts.append(f'<td>{before} → {after}</td>')
            parts.append(f'<td><span class="gain-cell"><span>{gain}</span>'
                         '<span class="gain-track" aria-hidden="true">'
                         f'<span class="gain-bar" style="left: {left:g}%; width: {width:g}%"></span>'
                         '</span></span></td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div></figure>')
    return '\n'.join(parts)+'\n'

abstract=paragraph((1,214,386))
architecture=figure('architecture',3,[100,81,513,324],[329,380])
architecture+=paragraph((1,688,734),(2,285,341),(3,605,630),(5,153,209),excerpts=[
    ('We introduce SPECTRA,','independently trained coarse and fine policies.'),
    ('To control the motion detail','a weighted sum of cosine curves.'),
    ('The coarse policy predicts','predicts the full action spectrum.'),
    ('A gate uses recent force history','without manually labeled contact phases.'),
    ('This allows policy selection','as the interaction unfolds.')])
simulation=paragraph((5,382,482),(5,505,594),excerpts=[
    ('We evaluate SPECTRA','two MimicGen tasks (Coffee and Threading).'),
    ('We compare Diffusion Policy','in action and DCT space (Table 1).')],
    citation_corrections=[('ManiSkill Mu et al. (2021) tasks','ManiSkill (Mu et al., 2021) tasks')],
    text_corrections=[(' (Table 1)','')])
simulation+=figure('policy-architectures',6,[108,84,505,202],[436,458],
    alt='(a) No force; (b) Always-on force; (c) Force gating; (d) SPECTRA')
simulation+=simulation_table()
simulation+=paragraph((5,616,684),excerpts=[
    ('Table 1 shows','DP and FM on all six tasks.'),
    ('PegInsertionSide remains','40.0% for SPECTRA.')],
    text_corrections=[('Table 1 shows that SPECTRA','SPECTRA')])
simulation+=paragraph((5,616,684),excerpts=[
    ('Its mean success rate','15.8 percentage points, respectively.')],
    text_corrections=[('Its mean success rate','SPECTRA’s mean success rate')])
normalization=paragraph((6,555,645),excerpts=[
    ('We compare SPECTRA','DCT-space diffusion baselines.')])
normalization+=normalization_table()
normalization+=paragraph((6,555,645),excerpts=[
    ('Table 2 shows','leaves PlugCharger performance unchanged.')],
    text_corrections=[('Table 2 shows that normalization','Normalization')])
real=paragraph((7,533,612),excerpts=[
    ('We evaluate SPECTRA','a wrist-mounted camera.')])
real+=paragraph((7,633,734),excerpts=[
    ('Coca-Cola placement additionally','the remaining tasks by success rate.')])
real+=(ROOT/'scripts/real_robot_videos.html').read_text()
real+=figure('real-robot-results',9,[108,81,504,200],[209,241])
real+=paragraph((8,599,689),excerpts=[
    ('Figure 5 shows','force-blind DP and FM on four of five tasks.'),
    ('Jigglypuff placement is the exception:','below FM’s 90%.')],
    text_corrections=[('Figure 5 shows that SPECTRA','SPECTRA')])
evaluation=''.join([
    evaluation_block('simulation','Simulation Performance',simulation),
    evaluation_block('spectral-normalization','Effect of Spectral Normalization',normalization),
    evaluation_block('real-robot','Real-Robot Performance',real),
])
interaction=paragraph((6,667,723),(7,441,508),excerpts=[
    ('We compare low-frequency','full-spectrum success on four of five tasks.')],
    text_corrections=[('Figure 3 shows that adding force','Adding force')])
interaction+=force_bandwidth_table()
interaction+=paragraph((6,667,723),(7,441,508),excerpts=[
    ('On PickCube,','full-spectrum success by 10 percentage points.')])
body=''.join([
    section('abstract','Abstract',abstract),
    section('architecture','Architecture',architecture),
    section('force-bandwidth','Force Benefits Depend on Action Bandwidth',interaction),
    section('experiments','Evaluation and Results',evaluation),
])
index=ROOT/'site/index.html';current=index.read_text()
citation=re.search(r'<section id="BibTeX".*?</section>',current,re.S).group()
current=re.sub(r'<main(?:\s[^>]*)?>.*?</main>',lambda _:'<main>\n'+body+citation+'\n</main>',current,flags=re.S)
current=current.replace('href="#paper"','href="#abstract"')
current=current.replace('  <link rel="stylesheet" href="static/vendor/katex/katex.min.css">\n','')
index.write_text(current)
manifest={'source_sha256':SOURCE_HASH,'scope':'Selected paper passages: abstract, architecture, force-versus-bandwidth ablation, simulation performance, policy comparisons, value of force feedback, spectral normalization, learned policy selection, and real-robot performance. In-text citations retained; approved text and citation formatting edits recorded. Source captions retained here for provenance, not displayed on the website. No PDF download.',
          'content':CONTENT}
(ROOT/'paper-port-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_HASH
assert not list((ROOT/'site').rglob('*.pdf'))
print('Generated curated project page with selected paper excerpts, 3 HTML results tables, paper figures, and 5 task demonstration loops.')
