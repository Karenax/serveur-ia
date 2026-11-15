"""Read-only CR export using Agent's existing ReportLab/Vera PDF runtime."""
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException


def build_pdf(project, meeting, actions):
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise HTTPException(503, 'Moteur PDF indisponible ; le compte rendu et son export Markdown restent conservés') from exc
    font_root = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in (('MeetingVera', 'Vera.ttf'), ('MeetingVeraBold', 'VeraBd.ttf')):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_root / filename)))
    body = ParagraphStyle('meeting_body', fontName='MeetingVera', fontSize=9, leading=13,
        spaceAfter=6, textColor=colors.HexColor('#18344D'), splitLongWords=True)
    heading = ParagraphStyle('meeting_heading', parent=body, fontName='MeetingVeraBold',
        fontSize=12, leading=17, spaceBefore=12, spaceAfter=7, keepWithNext=True)
    title = ParagraphStyle('meeting_title', parent=heading, fontSize=22, leading=28,
        textColor=colors.HexColor('#227A9D'))
    small = ParagraphStyle('meeting_small', parent=body, fontSize=8, leading=11,
        textColor=colors.HexColor('#526B7C'))

    def text(value, style=body):
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), style)

    story = [text('Compte rendu de réunion', title), text(f"{project['code']} - {project['title']}", heading),
        text(meeting['title'], heading), text(f"Date : {meeting['date'] or 'À préciser'}"),
        text(f"Participants : {meeting['participants'] or 'Non renseignés'}"), Spacer(1, 3*mm),
        text('Compte rendu et décisions', heading)]
    # Render safe text and simple headings; never execute HTML or fetch links.
    for line in (meeting['decisions'] or 'Aucune décision renseignée.').splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 2*mm))
        elif stripped.startswith('#'):
            story.append(text(stripped.lstrip('#').strip(), heading))
        else:
            story.append(text(line))
    story.append(text('Actions', heading))
    if not actions:
        story.append(text('Aucune action enregistrée.'))
    for index, action in enumerate(actions, 1):
        story.append(text(f"{index}. {action['title']}"))
        story.append(text(f"Responsable : {action['owner'] or 'À préciser'} | Échéance : {action['due_date'] or 'À préciser'}", small))
        story.append(text('Transférée en tâche' if action['task_id'] else 'À traiter', small))
        story.append(Spacer(1, 2*mm))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('MeetingVera', 8)
        canvas.setFillColor(colors.HexColor('#526B7C'))
        canvas.drawString(20*mm, 12*mm, 'Agent - Compte rendu de réunion')
        canvas.drawRightString(A4[0]-20*mm, 12*mm, f'Page {document.page}')
        canvas.restoreState()

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
        topMargin=18*mm, bottomMargin=22*mm, title=meeting['title'], author='Agent')
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
