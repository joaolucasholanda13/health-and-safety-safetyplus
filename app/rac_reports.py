"""Cálculo e apresentação do consolidado RAC e de seus anexos."""
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from io import BytesIO
import fitz
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Image

CORAL = colors.HexColor('#FF5246')
INK = colors.HexColor('#181818')
MUTED = colors.HexColor('#66615C')
LIGHT = colors.HexColor('#F4F2EF')


def adherence(answers, expected=None):
    answers = list(answers)
    expected = len(answers) if expected is None else expected
    answers = answers[:expected]
    ok = sum(a in {'ATENDE', 'SIM'} for a in answers)
    bad = sum(a in {'NAO_ATENDE', 'NAO'} for a in answers)
    na = answers.count('NA')
    pending = max(0, expected - ok - bad - na)
    score = 100 * ok / (ok + bad) if ok + bad else None
    state = 'Incompleta' if pending else ('Sem itens aplicáveis' if score is None else ('Meta atingida' if score >= 95 else 'Abaixo da meta'))
    return dict(ok=ok, bad=bad, na=na, pending=pending, score=score, state=state)


def percentage(value):
    return 'N/A' if value is None else f'{value:.1f}%'.replace('.', ',')


def plan_counts(answers, plans, today=None):
    today = today or datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    result = dict(not_started=0, progress=0, complete=0, late=0, opened=0)
    for index, answer in enumerate(answers):
        if answer not in {'NAO_ATENDE', 'NAO'}:
            continue
        plan = plans[index] if index < len(plans) and isinstance(plans[index], dict) else {}
        status = str(plan.get('status') or '').strip().casefold()
        if status in {'concluído', 'concluido', 'concluída', 'concluida'}:
            result['complete'] += 1
            continue
        result['opened'] += 1
        due = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                due = datetime.strptime(str(plan.get('due_date') or ''), fmt).date()
                break
            except ValueError:
                pass
        if status == 'atrasado' or (due and due < today):
            result['late'] += 1
        elif status == 'em andamento':
            result['progress'] += 1
        else:
            result['not_started'] += 1
    return result


def _paragraph(text, size=9, bold=False, color=INK):
    return Paragraph(escape(str(text or 'Não informado')).replace('\n', '<br/>'), ParagraphStyle(
        'rac', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size,
        leading=size * 1.4, textColor=color, spaceAfter=5))


def _table(rows, widths):
    table = Table([[_paragraph(v, 8, i == 0, colors.white if i == 0 else INK) for v in row] for i, row in enumerate(rows)], colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INK), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LINEBELOW', (0, 0), (-1, 0), 2, CORAL),
        ('LINEBELOW', (0, 1), (-1, -1), .4, colors.HexColor('#DEDAD5'))]))
    return table


def _append(doc, story, title, data, landscape=False):
    buffer = BytesIO()
    size = (792, 612) if landscape else (595.28, 841.89)
    def furniture(canvas, document):
        width, height = size
        canvas.setFillColor(CORAL); canvas.rect(32, height - 28, width - 64, 3, fill=1, stroke=0)
        canvas.setFont('Helvetica-Bold', 8); canvas.setFillColor(INK)
        canvas.drawString(32, height - 44, 'SAFETY PLUS  /  RAC')
        canvas.setFont('Helvetica', 8); canvas.setFillColor(MUTED)
        canvas.drawRightString(width - 32, height - 44, str(data.get('code') or 'Relatório'))
        canvas.line(32, 32, width - 32, 32)
        canvas.drawString(32, 20, title)
        canvas.drawRightString(width - 32, 20, f'Página {document.page}')
    SimpleDocTemplate(buffer, pagesize=size, leftMargin=32, rightMargin=32, topMargin=62, bottomMargin=46).build(story, onFirstPage=furniture, onLaterPages=furniture)
    with fitz.open(stream=buffer.getvalue(), filetype='pdf') as generated:
        doc.insert_pdf(generated)


def append_summary(doc, cfg, data):
    answers = list(data.get('answers') or [])
    plans = list(data.get('action_plans') or [])
    story = [_paragraph('Resultado consolidado', 20, True), _paragraph(cfg.get('title'), 10, color=MUTED), Spacer(1, 8)]
    story.append(_table([['Fornecedor / empresa', 'Site / ativo', 'Data da avaliação'],
        [data.get('contractor'), ' / '.join(str(data.get(k) or '') for k in ('cluster', 'site')).strip(' /'), data.get('inspection_date')]], [260, 310, 158]))
    story += [Spacer(1, 14), _paragraph('ADERÊNCIA POR SEÇÃO', 11, True)]
    rows = [['Seção', 'Atende', 'Não atende', 'N/A', 'Pendentes', 'Aderência', 'Meta', 'Situação']]
    action_rows = [['Seção', 'Não iniciado', 'Em andamento', 'Concluído', 'Atrasado', 'Abertos']]
    offset = 0
    for group in cfg.get('groups', []):
        count = len(group.get('items', [])); values = answers[offset:offset + count]
        metric = adherence(values, count)
        rows.append([group['name'], str(metric['ok']), str(metric['bad']), str(metric['na']), str(metric['pending']), percentage(metric['score']), '95%', metric['state']])
        counts = plan_counts(values, plans[offset:offset + count])
        action_rows.append([group['name']] + [str(counts[k]) for k in ('not_started', 'progress', 'complete', 'late', 'opened')])
        offset += count
    metric = adherence(answers, offset)
    rows.append(['GERAL', str(metric['ok']), str(metric['bad']), str(metric['na']), str(metric['pending']), percentage(metric['score']), '95%', metric['state']])
    story += [_table(rows, [322, 48, 60, 38, 58, 62, 40, 100]), Spacer(1, 7),
        _paragraph('Cálculo: Atende ÷ (Atende + Não atende) × 100. N/A não entra no denominador. O geral considera todos os itens, sem média de percentuais. Pendências impedem a conclusão; uma seção sem itens aplicáveis não recebe 100%.', 8, color=MUTED),
        Spacer(1, 10), _paragraph('PLANOS DE AÇÃO', 11, True), _table(action_rows, [278, 90, 90, 90, 90, 90]),
        _paragraph('Atrasado: prazo anterior a hoje e ação ainda não concluída. Os status são exclusivos; abertos = não iniciado + em andamento + atrasado.', 8, color=MUTED)]
    _append(doc, story, 'Consolidado de aderência e planos de ação', data, True)


def append_actions(doc, cfg, items, data):
    answers = list(data.get('answers') or []); plans = list(data.get('action_plans') or []); observations = list(data.get('observations') or [])
    story = []
    for index, item in enumerate(items):
        if index >= len(answers) or answers[index] not in {'NAO_ATENDE', 'NAO'}:
            continue
        plan = plans[index] if index < len(plans) and isinstance(plans[index], dict) else {}
        if story: story.append(Spacer(1, 16))
        story.append(KeepTogether([_paragraph(f"PLANO DE AÇÃO  /  ITEM {item.get('number', index+1)}", 13, True, CORAL), _paragraph(cfg.get('title'), 9, color=MUTED), _paragraph(item.get('text'), 10, True)]))
        counts = plan_counts([answers[index]], [plan])
        status = next(label for key, label in [('late', 'Atrasado'), ('complete', 'Concluído'), ('progress', 'Em andamento'), ('not_started', 'Não iniciado')] if counts[key])
        meta = [['Responsável', 'Prazo', 'Status'], [plan.get('responsible'), plan.get('due_date'), status]]
        story += [_table(meta, [235, 132, 164]), Spacer(1, 10)]
        for label, value in [('Observação / evidência', observations[index] if index < len(observations) else ''), ('Ação corretiva', plan.get('action'))]:
            story.append(KeepTogether([_paragraph(label.upper(), 8, True, MUTED), _paragraph(value, 10)]) if len(str(value or '')) < 1500 else _paragraph(label.upper(), 8, True, MUTED))
            if len(str(value or '')) >= 1500: story.append(_paragraph(value, 10))
    if story: _append(doc, story, 'Anexo • Planos de ação', data)


def append_photos(doc, cfg, items, data, resolve):
    story = []
    for index, photos in enumerate(data.get('evidence_photos') or []):
        if index >= len(items): break
        for number, rel in enumerate(photos if isinstance(photos, list) else [photos], 1):
            path = resolve(rel)
            if not path: continue
            if story: story.append(PageBreak())
            story += [_paragraph('EVIDÊNCIA FOTOGRÁFICA', 18, True), _paragraph(f"{cfg.get('title')} / Item {items[index].get('number', index+1)} / Foto {number}", 9, color=MUTED), _paragraph(items[index].get('text'), 10, True)]
            observations = data.get('observations') or []
            if index < len(observations) and observations[index]: story.append(_paragraph(observations[index], 9))
            try:
                picture = Image(str(path)); picture._restrictSize(531, 480)
                story += [Spacer(1, 10), picture]
            except Exception:
                story.append(_paragraph('Não foi possível exibir esta imagem. Consulte o arquivo anexado.'))
    if story: _append(doc, story, 'Anexo • Evidências fotográficas', data)
