"""Render private, factual JSON into a selectable-text, single-column CV."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether


def fonts():
    base = Path('/usr/share/fonts/truetype/lato')
    if (base / 'Lato-Regular.ttf').exists():
        pdfmetrics.registerFont(TTFont('Body', str(base / 'Lato-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('BodyBold', str(base / 'Lato-Bold.ttf')))
        pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold')
        return 'Body', 'BodyBold'
    return 'Helvetica', 'Helvetica-Bold'


def render(data: dict, output: Path):
    regular, bold = fonts()
    ink, muted, accent = '#192F36', '#54666C', '#246C6A'
    styles = {
        'name': ParagraphStyle('name', fontName=bold, fontSize=25, leading=29, textColor=colors.HexColor(ink)),
        'headline': ParagraphStyle('headline', fontName=regular, fontSize=11, leading=15, textColor=colors.HexColor(accent)),
        'body': ParagraphStyle('body', fontName=regular, fontSize=9.4, leading=12.6, textColor=colors.HexColor(ink)),
        'small': ParagraphStyle('small', fontName=regular, fontSize=8.8, leading=12, textColor=colors.HexColor(muted)),
        'section': ParagraphStyle('section', fontName=bold, fontSize=9, leading=13, spaceBefore=12, spaceAfter=5, textColor=colors.HexColor(accent)),
        'title': ParagraphStyle('title', fontName=bold, fontSize=10.2, leading=14, textColor=colors.HexColor(ink)),
        'bullet': ParagraphStyle('bullet', fontName=regular, fontSize=9.4, leading=12.6, leftIndent=9, firstLineIndent=-9, spaceAfter=3, textColor=colors.HexColor(ink)),
    }
    story = []
    def p(text, style='body'):
        return Paragraph(text, styles[style])
    def section(title):
        story.append(p(title.upper(), 'section'))
    story += [p(escape(data['name']), 'name'), Spacer(1, 3), p(escape(data['headline']), 'headline'), Spacer(1, 7)]
    contacts = [escape(data['location']), f'<link href={quoteattr("mailto:" + data["email"])}>{escape(data["email"])}</link>']
    contacts += [f'<link href={quoteattr(link["url"])}>{escape(link["label"])}</link>' for link in data.get('links', [])]
    story += [p('  ·  '.join(contacts), 'small'), Spacer(1, 11), HRFlowable(width='100%', thickness=1, color=colors.HexColor(accent)), Spacer(1, 10), p(escape(data['summary']))]
    section('Education')
    for item in data['education']:
        story += [KeepTogether([p(escape(item['title']) + ' <font color="' + muted + '">| ' + escape(item['dates']) + '</font>', 'title'), p(escape(item['organization'])), p(escape(item['detail']), 'small')]), Spacer(1, 6)]
    section('Selected research projects')
    for item in data['projects']:
        block = [p(escape(item['title']) + ' <font color="' + muted + '">| ' + escape(item['dates']) + '</font>', 'title'), Spacer(1, 3)]
        block += [p('•  ' + escape(b), 'bullet') for b in item['bullets']]
        story += [KeepTogether(block), Spacer(1, 5)]
    section('Experience')
    for item in data['experience']:
        block = [p(escape(item['title']) + ' | ' + escape(item['dates']), 'title'), p(escape(item['organization']), 'small'), Spacer(1, 3)]
        block += [p('•  ' + escape(b), 'bullet') for b in item['bullets']]
        story.append(KeepTogether(block))
    section('Technical skills')
    for item in data['skills']:
        story.append(p('<b>' + escape(item['label']) + ':</b> ' + escape(item['text'])))
    section('Selected coursework')
    story.append(p(escape(data['coursework']), 'small'))
    section('Languages')
    story.append(p(escape(data['languages'])))
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=39, rightMargin=39, topMargin=32, bottomMargin=30, title=data['name'] + ' | Curriculum Vitae', author=data['name'])
    doc.build(story)
    from pypdf import PdfReader
    if len(PdfReader(output).pages) != 1:
        raise ValueError('CV exceeds one page: shorten content before using this PDF.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    render(json.loads(args.source.read_text()), args.output)
    print(args.output)


if __name__ == '__main__':
    main()
