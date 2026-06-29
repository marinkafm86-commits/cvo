from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (Table, TableStyle, Paragraph, Spacer,
                                 HRFlowable, KeepTogether, BaseDocTemplate,
                                 PageTemplate, Frame)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os

app = Flask(__name__)
CORS(app)

# Fonts
BASE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(BASE, 'logo.png')

def register_fonts():
    fonts_dir = '/usr/share/fonts/truetype'
    try:
        pdfmetrics.registerFont(TTFont('Lora', f'{fonts_dir}/google-fonts/Lora-Variable.ttf'))
        pdfmetrics.registerFont(TTFont('Lora-I', f'{fonts_dir}/google-fonts/Lora-Italic-Variable.ttf'))
    except:
        pass
    try:
        pdfmetrics.registerFont(TTFont('DJ', f'{fonts_dir}/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DJB', f'{fonts_dir}/dejavu/DejaVuSans-Bold.ttf'))
    except:
        # fallback to Helvetica if fonts not available
        pass

try:
    register_fonts()
    FONT = 'DJ'
    FONT_B = 'DJB'
    FONT_TITLE = 'Lora'
    FONT_ITALIC = 'Lora-I'
except:
    FONT = 'Helvetica'
    FONT_B = 'Helvetica-Bold'
    FONT_TITLE = 'Helvetica-Bold'
    FONT_ITALIC = 'Helvetica-Oblique'

GOLD   = colors.HexColor('#C9A84C')
GOLD_L = colors.HexColor('#E8D5A3')
BLACK  = colors.HexColor('#1A1A1A')
GRAY_L = colors.HexColor('#F5F3EE')
GRAY_M = colors.HexColor('#E8E4DC')
GRAY_T = colors.HexColor('#666666')
HDR_T  = colors.HexColor('#4A3A0A')
WHITE  = colors.white
W, H   = A4

def fmt(v):
    if v is None or v == '' or v == 0 and str(v) != '0': return '—'
    try: return f'{int(float(v)):,}'.replace(',', '\u00a0')
    except: return str(v) if v else '—'

def make_doc(buf, manager):
    doc = BaseDocTemplate(buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=48*mm, bottomMargin=25*mm)
    def hf(c, doc):
        c.saveState()
        c.setFillColor(GOLD)
        c.rect(0, H-10*mm, W, 10*mm, fill=1, stroke=0)
        if os.path.exists(LOGO):
            lw = 65*mm; lh = lw*(1805/4168)
            c.drawImage(LOGO, 18*mm, H-8*mm-lh, width=lw, height=lh, mask='auto')
        rx = W-18*mm
        c.setFont(FONT, 7.5); c.setFillColor(GRAY_T)
        c.drawRightString(rx, H-16*mm, '+7 (3452) 99-59-19')
        c.drawRightString(rx, H-22*mm, 'cvo@maxim-rest.ru')
        c.drawRightString(rx, H-28*mm, 'maxim-rest.ru')
        c.setFont(FONT, 7)
        c.drawRightString(rx, H-34*mm, f'Ваш менеджер: {manager}')
        c.setStrokeColor(GOLD); c.setLineWidth(0.5)
        c.line(18*mm, 18*mm, W-18*mm, 18*mm)
        c.setFont(FONT, 7); c.setFillColor(GRAY_T)
        c.drawString(18*mm, 11*mm, 'Центр Выездного Обслуживания МАКСИМ')
        c.drawRightString(W-18*mm, 11*mm, f'стр. {doc.page}')
        c.restoreState()
    frame = Frame(18*mm, 25*mm, W-36*mm, H-73*mm, id='main')
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=hf)])
    return doc

CW = W - 36*mm

def S():
    return {
        'title': ParagraphStyle('t', fontName=FONT_TITLE, fontSize=18, textColor=BLACK, spaceAfter=4*mm),
        'label': ParagraphStyle('l', fontName=FONT, fontSize=7.5, textColor=GRAY_T, leading=10),
        'value': ParagraphStyle('v', fontName=FONT_B, fontSize=8.5, textColor=BLACK, leading=11),
        'sec':   ParagraphStyle('s', fontName=FONT_B, fontSize=7.5, textColor=WHITE, leading=10),
        'item':  ParagraphStyle('i', fontName=FONT, fontSize=8, textColor=BLACK, leading=10),
        'ib':    ParagraphStyle('ib', fontName=FONT_B, fontSize=8, textColor=BLACK, leading=11),
        'note':  ParagraphStyle('n', fontName=FONT_ITALIC, fontSize=7.5, textColor=GRAY_T, leading=10),
    }

def info_tbl(data, s):
    rows = []
    for i in range(0, len(data), 2):
        l, r = data[i], (data[i+1] if i+1<len(data) else ('',''))
        rows.append([Paragraph(l[0],s['label']), Paragraph(str(l[1]),s['value']),
                     Paragraph(r[0],s['label']), Paragraph(str(r[1]),s['value'])])
    cw = CW/4
    t = Table(rows, colWidths=[cw*.7,cw*1.3,cw*.7,cw*1.3])
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                            ('BOTTOMPADDING',(0,0),(-1,-1),3),
                            ('TOPPADDING',(0,0),(-1,-1),2)]))
    return t

def sec_hdr(title, s):
    t = Table([[Paragraph(title.upper(), s['sec'])]], colWidths=[CW])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GOLD),
                            ('TOPPADDING',(0,0),(-1,-1),4),
                            ('BOTTOMPADDING',(0,0),(-1,-1),4),
                            ('LEFTPADDING',(0,0),(-1,-1),6)]))
    return t

def menu_tbl(items, s):
    cw = [CW*0.42, CW*0.10, CW*0.09, CW*0.13, CW*0.13, CW*0.13]
    hdr = ['Наименование', 'Выход, г', 'Кол-во', 'Цена, ₽', 'Сумма, ₽', 'Вес, г']
    rows = [hdr]
    for item in items:
        name = item.get('name','')
        gram = item.get('gram')
        qty  = item.get('qty')
        price= item.get('price')
        total= item.get('total', (qty or 0)*(price or 0))
        weight = (gram or 0)*(qty or 0)
        rows.append([Paragraph(name, s['item']),
                     fmt(gram), fmt(qty), fmt(price), fmt(total),
                     fmt(weight) if weight else '—'])
    t = Table(rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),GOLD_L),
        ('FONTNAME',(0,0),(-1,0),FONT_B),('FONTSIZE',(0,0),(-1,0),7.5),
        ('TEXTCOLOR',(0,0),(-1,0),HDR_T),
        ('ALIGN',(1,0),(-1,0),'CENTER'),('ALIGN',(0,0),(0,0),'LEFT'),
        ('LINEBELOW',(0,0),(-1,0),0.8,GOLD),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,GRAY_L]),
        ('FONTNAME',(0,1),(-1,-1),FONT),('FONTSIZE',(0,1),(-1,-1),7.5),
        ('TEXTCOLOR',(0,1),(-1,-1),BLACK),
        ('ALIGN',(1,1),(-1,-1),'CENTER'),('ALIGN',(0,1),(0,-1),'LEFT'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(0,-1),6),
        ('GRID',(0,0),(-1,-1),0.3,GRAY_M),
    ]))
    return t

def section(title, items, s, spacer_after=True):
    hdr = sec_hdr(title, s)
    tbl = menu_tbl(items, s)
    elems = []
    if len(items) <= 8:
        elems.append(KeepTogether([hdr, tbl]))
    else:
        elems.append(KeepTogether([hdr, tbl]))
    if spacer_after:
        elems.append(Spacer(1, 2*mm))
    return elems

def svc_tbl(services, s):
    cw = [CW*.46, CW*.12, CW*.16, CW*.26]
    hdr = ['Наименование', 'Кол-во', 'Цена, ₽', 'Сумма, ₽']
    rows = [hdr]
    for sv in services:
        note = sv.get('note','')
        name_p = Paragraph(
            sv['name'] + (f'<br/><font color="#999999" size="6.5">{note}</font>' if note else ''),
            s['item'])
        rows.append([name_p, fmt(sv.get('qty')), fmt(sv.get('price')), fmt(sv.get('total'))+'  ₽'])
    t = Table(rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),GOLD_L),
        ('FONTNAME',(0,0),(-1,0),FONT_B),('FONTSIZE',(0,0),(-1,0),7.5),
        ('TEXTCOLOR',(0,0),(-1,0),HDR_T),
        ('ALIGN',(1,0),(-1,0),'CENTER'),('ALIGN',(0,0),(0,0),'LEFT'),
        ('LINEBELOW',(0,0),(-1,0),0.8,GOLD),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,GRAY_L]),
        ('FONTNAME',(0,1),(-1,-1),FONT),('FONTSIZE',(0,1),(-1,-1),7.5),
        ('TEXTCOLOR',(0,1),(-1,-1),BLACK),
        ('ALIGN',(1,1),(-1,-1),'CENTER'),('ALIGN',(0,1),(0,-1),'LEFT'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(0,-1),6),
        ('GRID',(0,0),(-1,-1),0.3,GRAY_M),
    ]))
    return t

def gram_row_el(food_g, s):
    data = [[Paragraph(f'Выход еды на персону: <b>{food_g} г</b>', s['item']),
             Paragraph('Выход напитков на персону: по нормативу', s['item'])]]
    t = Table(data, colWidths=[CW*.5, CW*.5])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),GRAY_M),
                            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                            ('LEFTPADDING',(0,0),(0,-1),6),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    return t

def totals_el(food, svc, grand, persons, pp, s):
    data = [
        [Paragraph('Итого за меню', s['item']), Paragraph(f'{fmt(food)} ₽', s['item'])],
        [Paragraph('Итого за услуги', s['item']), Paragraph(f'{fmt(svc)} ₽', s['item'])],
        [Paragraph('ИТОГО К ОПЛАТЕ', s['ib']), Paragraph(f'{fmt(grand)} ₽', s['ib'])],
        [Paragraph(f'Средний чек на персону ({persons} чел.)', s['label']),
         Paragraph(f'{fmt(pp)} ₽/чел.', s['label'])],
    ]
    t = Table(data, colWidths=[CW*.65, CW*.35])
    t.setStyle(TableStyle([
        ('ALIGN',(1,0),(-1,-1),'RIGHT'),
        ('LINEBELOW',(0,1),(-1,1),0.3,GRAY_M),
        ('LINEABOVE',(0,2),(-1,2),1,GOLD),('LINEBELOW',(0,2),(-1,2),1,GOLD),
        ('TEXTCOLOR',(0,2),(-1,2),GOLD),
        ('FONTNAME',(0,2),(-1,2),FONT_B),('FONTSIZE',(0,2),(-1,2),11),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
    ]))
    return t


def generate_pdf(data):
    s = S()
    buf = io.BytesIO()
    doc = make_doc(buf, data.get('manager',''))
    story = []

    story.append(Paragraph('Коммерческое предложение', s['title']))
    story.append(HRFlowable(width=CW, thickness=0.5, color=GOLD, spaceAfter=4*mm))

    f = data.get('form', {})
    info_data = [
        ('Заказчик', f.get('client','')),
        ('Контактное лицо', f.get('contact_name','')),
        ('Телефон', f.get('contact_phone','')),
        ('Электронная почта', f.get('contact_email','')),
        ('Адрес мероприятия', f.get('address','')),
        ('Дата и время', f.get('datetime_str','')),
        ('Формат мероприятия', f.get('format_name','')),
        ('Количество персон', f.get('persons_str','')),
        ('Форма оплаты', f.get('payment','')),
        ('', ''),
    ]
    story.append(info_tbl(info_data, s))
    story.append(Spacer(1, 5*mm))

    # Menu sections
    sections = data.get('sections', [])
    for i, sec in enumerate(sections):
        is_last = (i == len(sections) - 1)
        story += section(sec['title'], sec['items'], s, spacer_after=not is_last)

    # Gram row
    if data.get('gram_cold_pp'):
        story.append(Spacer(1, 3*mm))
        story.append(gram_row_el(data['gram_cold_pp'], s))

    story.append(Spacer(1, 4*mm))

    # Services
    services = data.get('services', [])
    if services:
        story.append(KeepTogether([sec_hdr('Прочие расходы и услуги', s), svc_tbl(services, s)]))

    story.append(Spacer(1, 6*mm))

    food_total = data.get('food_total', 0)
    svc_total  = data.get('service_total', 0)
    grand      = food_total + svc_total
    persons    = data.get('persons', 1)
    pp         = round(grand / persons) if persons else 0

    story.append(totals_el(food_total, svc_total, grand, persons, pp, s))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        'Предложение действительно 5 дней с момента выставления. '
        'По вопросам обращайтесь к вашему менеджеру ЦВО Максим.', s['note']))

    doc.build(story)
    buf.seek(0)
    return buf


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/generate-pdf', methods=['POST', 'OPTIONS'])
def generate():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json(force=True)
        pdf_buf = generate_pdf(data)
        client = data.get('form', {}).get('client', 'КП').replace(' ', '_')[:30]
        filename = f'КП_{client}.pdf'
        return send_file(
            pdf_buf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
