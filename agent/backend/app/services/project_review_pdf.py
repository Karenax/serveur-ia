"""PDF generated solely from a frozen, human-validated RLP snapshot."""
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException


def build_pdf(snapshot):
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise HTTPException(503, 'Moteur PDF indisponible : installer les dépendances Agent ; brouillon conservé') from exc
    from .project_reviews import SECTIONS
    from .project_identity import ROLE_LABELS
    statuses = {'draft': 'Brouillon', 'to_verify': 'À vérifier', 'validated': 'Validé',
                'to_revise': 'À réviser', 'archived': 'Archivé'}
    font_root = Path(reportlab.__file__).parent / 'fonts'
    # ReportLab bundles these fonts, so rendering does not depend on Office,
    # a network drive, a Windows user font or an external API.
    for name, filename in (('ReviewVera', 'Vera.ttf'), ('ReviewVeraBold', 'VeraBd.ttf')):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_root / filename)))
    navy = colors.HexColor('#18344D')
    blue = colors.HexColor('#227A9D')
    body = ParagraphStyle('review_body', fontName='ReviewVera', fontSize=9, leading=13,
                          spaceAfter=5, textColor=navy, splitLongWords=True)
    heading = ParagraphStyle('review_heading', parent=body, fontName='ReviewVeraBold', fontSize=12,
                             leading=16, spaceBefore=12, spaceAfter=7, keepWithNext=True)
    title = ParagraphStyle('review_title', parent=heading, fontSize=22, leading=28, textColor=blue)
    small = ParagraphStyle('review_small', parent=body, fontSize=7, leading=10, textColor=colors.HexColor('#526B7C'))

    def text(value, style=body):
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), style)

    project, review = snapshot['project'], snapshot['review']
    content = review['content']
    story = [text('Revue de lancement de projet', title),
             text(f"{project['code']} - {project['title']}", heading),
             text(f"Révision {review['number']} | Date : {content['meeting_date']} | Lieu : {content['location'] or '-'}"),
             text(f"Publication : {snapshot['published_at']} | Auteur : {snapshot['published_by']}", small),
             Spacer(1, 4 * mm), text('Participants', heading)]
    table = Table([[text('Nom', small), text('Fonction', small), text('Signature prévue', small)]] + [
        [text(person['name']), text(person['function'] or '-'), text('Oui' if person['signature_required'] else 'Non')]
        for person in content['participants']], colWidths=[65 * mm, 70 * mm, 35 * mm], repeatRows=1,
        hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EAF3F7')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                               ('LINEBELOW', (0, 0), (-1, 0), 0.4, blue)]))
    story.append(table)
    if content['notes']:
        story.append(text('Contexte et notes', heading))
        # Independent paragraphs allow a long meeting context to start below
        # participants, instead of pushing its whole block to a blank page.
        story.extend(text(line) if line.strip() else Spacer(1, 2 * mm) for line in content['notes'].split('\n'))
    for section in SECTIONS:
        items = [item for item in content['items'] if item['section_code'] == section['code']]
        if not items:
            continue
        story.append(text(section['label'], heading))
        for number, item in enumerate(items, 1):
            label = text(f"{number}. {item['text']}")
            label.keepWithNext = bool(item['owner'] or item['due_date'] or item['evidence_ids'])
            story.append(label)
            if item['owner'] or item['due_date']:
                story.append(text(f"Responsable : {item['owner'] or '-'} | Échéance : {item['due_date'] or '-'}", small))
            for evidence_id in item['evidence_ids']:
                proof = review['provenance'][evidence_id]
                source = text(f"Source audio {proof['recording_id']} - transcription v{proof['revision']} - "
                              f"{proof['speaker']} ({proof['start']} à {proof['end']} s)", small)
                source.keepWithNext = True
                story.extend([source, text(f"Citation : {proof['quote']}", small)])
    story.append(text('Livrables et contrôles retenus', heading))
    for deliverable in snapshot['deliverables']:
        story.append(text(f"{deliverable['title']} | État documentaire : {statuses.get(deliverable['document_status'], deliverable['document_status'])}"))
        for check in deliverable['checklist']:
            if check['active']:
                story.append(text(f"{'Vérifié' if check['completed'] else 'À traiter'} - {check['label']}", small))
    story.extend([text('Équipe projet au moment de la publication', heading)])
    for member in snapshot['team']:
        story.append(text(f"{member['name']} - {ROLE_LABELS.get(member['role'], member['role'])}", small))

    def page(canvas, document):
        canvas.setFont('ReviewVera', 7)
        canvas.setFillColor(navy)
        canvas.drawString(20 * mm, 13 * mm, f"Agent | RLP {review['number']} | Publication {snapshot['publication_id']}")
        canvas.drawRightString(A4[0] - 20 * mm, 13 * mm, f'Page {document.page}')

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                                 topMargin=18 * mm, bottomMargin=23 * mm,
                                 title=f"RLP {project['code']} - révision {review['number']}", author='Agent')
    document.build(story, onFirstPage=page, onLaterPages=page)
    return output.getvalue()
