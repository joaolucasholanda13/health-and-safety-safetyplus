from __future__ import annotations
from pathlib import Path
import os
import hmac
import hashlib
import fitz
import io
import qrcode
import qrcode.image.svg
from .module_configs import MODULES, VEHICLE_DAYS, VEHICLE_ITEM_NUMBERS, INSPECTION_MODULES, DOCUMENT_TITLES, CHECKLIST, RAC_MODULES
from .rac_pdf_layouts import RAC_PDF_LAYOUTS

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / 'pdf_templates'
RAC_TEMPLATE_DIR = BASE_DIR / 'rac_templates'
STORAGE_DIR = Path(os.getenv('STORAGE_DIR', str(BASE_DIR.parent / 'storage'))).resolve()


def safe_filename(text: str) -> str:
    chars=[]
    for ch in str(text):
        chars.append(ch if (ch.isalnum() or ch in '-_ .') else '_')
    return ''.join(chars).strip().replace(' ','_')[:120] or 'documento'


def _fit_textbox(page, rect, text, fontsize=7.0, min_fontsize=4.2, align=0, bold=False):
    text=(text or '').strip()
    if not text: return
    fontname='hebo' if bold else 'helv'
    fs=float(fontsize)
    while fs >= min_fontsize:
        rc=page.insert_textbox(rect,text,fontsize=fs,fontname=fontname,align=align,color=(0,0,0),lineheight=1.05)
        if rc >= 0: return
        fs -= .35
    page.insert_textbox(rect,text,fontsize=min_fontsize,fontname=fontname,align=align,color=(0,0,0),lineheight=1.0)


def _sig_abs(value: str | None) -> Path | None:
    if not value: return None
    p=Path(value)
    if not p.is_absolute(): p=STORAGE_DIR / p
    return p if p.exists() else None


def _sig_stamp(value) -> str:
    """Data/hora da assinatura: lida do nome do arquivo (AAAAMMDD_HHMMSS) ou, se faltar, da data do arquivo."""
    p=_sig_abs(value)
    if not p: return ''
    import re as _re
    from datetime import datetime as _dt
    m=_re.search(r'(\d{8})_(\d{6})',Path(p).name)
    try:
        if m: return _dt.strptime(m.group(1)+m.group(2),'%Y%m%d%H%M%S').strftime('%d/%m/%Y %H:%M')
        return _dt.fromtimestamp(Path(p).stat().st_mtime).strftime('%d/%m/%Y %H:%M')
    except Exception:
        return ''


def _sig_enhanced(path):
    """Rubrica mais visível: tinta escura e encorpada, fundo transparente, recortada rente ao traço."""
    from PIL import Image, ImageOps, ImageFilter
    im=Image.open(path); im.load()
    rgba=im.convert('RGBA'); alpha=rgba.split()[-1]
    if alpha.getextrema()[0]<250:
        mask=alpha
    else:
        mask=ImageOps.invert(ImageOps.autocontrast(rgba.convert('L')))
        mask=mask.point(lambda v: 0 if v<28 else min(255,int(v*1.8)))
    if max(rgba.size)<1000:
        k=1000/max(rgba.size); size=(int(rgba.width*k),int(rgba.height*k)); mask=mask.resize(size,Image.LANCZOS)
    mask=mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.8)).point(lambda v: min(255,int(v*1.6)))
    box=mask.getbbox()
    if not box: return None
    pad=8; box=(max(0,box[0]-pad),max(0,box[1]-pad),min(mask.width,box[2]+pad),min(mask.height,box[3]+pad))
    mask=mask.crop(box)
    out=Image.new('RGBA',mask.size,(8,16,60,0)); out.putalpha(mask)
    buf=io.BytesIO(); out.save(buf,'PNG'); return buf.getvalue()


def _add_signature(page, rect, value: str | None, stamp: bool = True) -> bool:
    p=_sig_abs(value)
    if not p: return False
    try:
        data=_sig_enhanced(p)
    except Exception:
        data=None
    txt=_sig_stamp(value) if stamp else ''
    img_rect=fitz.Rect(rect); st_rect=None
    if txt and rect.height>=11 and rect.width>=24:
        if rect.width/rect.height>3.4:   # célula larga e baixa: carimbo à direita
            cut=rect.x0+rect.width*0.62; img_rect=fitz.Rect(rect.x0,rect.y0,cut,rect.y1); st_rect=fitz.Rect(cut,rect.y0,rect.x1,rect.y1)
        else:                            # carimbo embaixo
            band=min(max(rect.height*0.27,4.6),9); img_rect=fitz.Rect(rect.x0,rect.y0,rect.x1,rect.y1-band); st_rect=fitz.Rect(rect.x0,rect.y1-band,rect.x1,rect.y1)
    try:
        if data: page.insert_image(img_rect,stream=data,keep_proportion=True,overlay=True)
        else: page.insert_image(img_rect,filename=str(p),keep_proportion=True,overlay=True)
        if st_rect is not None:
            short=txt if st_rect.width>=58 else txt[:-6]+txt[-5:]  # sem o ano quando a célula é estreita
            if st_rect.width<58: short=txt[:5]+' '+txt[-5:]
            fs=max(3.4,min(6.2,st_rect.width/(len(short)*0.52),st_rect.height*0.9))
            tw=fitz.get_text_length(short,fontname='hebo',fontsize=fs)
            page.insert_text((st_rect.x0+max(0,(st_rect.width-tw)/2),st_rect.y0+st_rect.height/2+fs*0.35),short,fontsize=fs,fontname='hebo',color=(.05,.05,.25))
        return True
    except Exception:
        return False


def _add_item_signature(page, rect, item: dict) -> bool:
    return _add_signature(page,rect,(item or {}).get('signature_image'),stamp=False)


def _publish(doc, out_pdf: Path):
    out_pdf.parent.mkdir(parents=True,exist_ok=True)
    tmp=out_pdf.with_name(out_pdf.stem+'.__tmp__.pdf')
    if tmp.exists(): tmp.unlink()
    doc.save(tmp,garbage=4,deflate=True)
    doc.close()
    check=fitz.open(tmp)
    pages=check.page_count; check.close()
    if pages < 1: raise RuntimeError('PDF inválido.')
    os.replace(tmp,out_pdf)
    return out_pdf


def _severity_code(value: str | None) -> str:
    value=(value or '').strip().upper()
    if not value:
        return ''
    # Compatibilidade com APRs antigas (Baixo/Médio/Alto) e novo padrão A/B/C.
    legacy={'ALTO':'A','MÉDIO':'B','MEDIO':'B','BAIXO':'C'}
    if value in legacy:
        return legacy[value]
    if value in {'A','B','C'}:
        return value
    return value


def _replace_template_field(page, rect, text, fontsize=6.2, min_fontsize=5.0, align=1, bold=False):
    """Reforma visualmente o campo do modelo e reinsere o valor centralizado.
    Usado nos campos Data/Hora da APR para não sobrepor os caracteres '/' e 'h' do PDF original.
    Em vez de deixar um bloco branco "estourado", aplica exatamente o tom de fundo
    da APR original (#EDE9E5), sem borda, para o campo parecer parte do próprio formulário.
    """
    r=fitz.Rect(*rect) if not isinstance(rect,fitz.Rect) else rect
    # Cor real do fundo da APR original (#EDE9E5 / RGB 237,233,229).
    # Sem borda: o campo se integra ao documento e elimina a aparência de tarja branca.
    fill=(237/255,233/255,229/255)
    page.draw_rect(r,color=fill,fill=fill,width=0,overlay=True)
    inner=fitz.Rect(r.x0+1.5,r.y0+0.4,r.x1-1.5,r.y1-0.4)
    _fit_textbox(page,inner,text,fontsize,min_fontsize,align,bold)


def _header_apr(page,data,page_no):
    severity=data.get('severity','')
    if page_no==0:
        _fit_textbox(page,fitz.Rect(53,52,151,63),data.get('cluster',''),6.2)
        _fit_textbox(page,fitz.Rect(186,52,245,63),severity,6.1,5.0,1,True)
        _fit_textbox(page,fitz.Rect(276,52,438,63),data.get('activity',''),6.2)
        # O modelo possui "/ /" e "h" impressos. Limpamos apenas a área de preenchimento
        # para manter Data e Hora totalmente dentro dos respectivos campos.
        _replace_template_field(page,(558,52.2,624,62.2),data.get('apr_date',''),5.8,5.0,1,False)
        _replace_template_field(page,(646,52.2,680,62.2),data.get('apr_time',''),5.8,5.0,1,False)
    elif page_no==1:
        _fit_textbox(page,fitz.Rect(53,84.5,166,96),data.get('cluster',''),6.3)
        _fit_textbox(page,fitz.Rect(202,84.5,279,96),severity,6.2,5.0,1,True)
        _fit_textbox(page,fitz.Rect(310,84.5,481,96),data.get('activity',''),6.3)
        _replace_template_field(page,(501,84.5,574,95.5),data.get('apr_date',''),5.9,5.0,1,False)
        _replace_template_field(page,(601,84.5,638,95.5),data.get('apr_time',''),5.9,5.0,1,False)
    else:
        _fit_textbox(page,fitz.Rect(79,108,283,126),data.get('cluster',''),10)
        _fit_textbox(page,fitz.Rect(343,108,482,126),severity,9.5,7.0,1,True)
        _fit_textbox(page,fitz.Rect(534,108,824,126),data.get('activity',''),10)
        _replace_template_field(page,(874,108.5,1006,125.5),data.get('apr_date',''),9.2,7.2,1,False)
        _replace_template_field(page,(1049,108.5,1115,125.5),data.get('apr_time',''),9.2,7.2,1,False)


def _critical_activity_summary(data: dict) -> tuple[str, str]:
    critical='SIM' if str(data.get('critical_activity','')).strip().upper()=='SIM' else 'NÃO'
    permits=[str(x).strip() for x in (data.get('critical_permits') or []) if str(x).strip()]
    return critical, ', '.join(permits)



def _append_apr_daily_signatures(doc, data: dict) -> None:
    """Anexa ao PDF da APR a folha de assinaturas diárias da equipe (até 7 dias)."""
    workers=[dict(w or {}) for w in (data.get('workers') or []) if (w or {}).get('worker') or (w or {}).get('name')]
    if not workers:
        return
    from datetime import datetime, timedelta
    periods=[]
    try:
        original=datetime.strptime(str(data.get('apr_date') or ''),'%d/%m/%Y').date()
        periods.append(('Período original',[original+timedelta(days=i) for i in range(7)]))
    except Exception:
        pass
    for row in data.get('approvals') or []:
        if not isinstance(row,dict) or str(row.get('type') or '').strip().lower()!='revalidação':
            continue
        try:
            first=datetime.strptime(str(row.get('start') or ''),'%d/%m/%Y').date()
            last=datetime.strptime(str(row.get('end') or ''),'%d/%m/%Y').date()
            if first<=last:
                periods.append((f'Revalidação {len(periods)}',[first+timedelta(days=i) for i in range(min((last-first).days+1,7))]))
        except Exception:
            continue
    if not periods: return
    page_w,page_h=842,595  # A4 paisagem
    margin=22
    name_w=184
    day_w=(page_w-2*margin-name_w)/7.0
    row_h=52
    rows_per_page=8
    day_names=('Seg','Ter','Qua','Qui','Sex','Sáb','Dom')
    for period_title,days in periods:
        for start_idx in range(0,len(workers),rows_per_page):
            page=doc.new_page(width=page_w,height=page_h)
            page.insert_text((margin,28),f'APR — ASSINATURAS DIÁRIAS — {period_title}',fontsize=12,fontname='hebo')
            page.insert_text((margin,43),f"{data.get('code','')}  |  {data.get('activity','')}  |  Validade: {days[0].strftime('%d/%m/%Y')} a {days[-1].strftime('%d/%m/%Y')}",fontsize=7,fontname='helv')
            # QR geral: todos usam o mesmo código e, após login, cada usuário assina apenas a própria participação.
            try:
                domain=(os.getenv('DOMAIN','safetyplus.tech') or 'safetyplus.tech').strip().strip('/')
                base=domain if domain.startswith(('http://','https://')) else 'https://'+domain
                doc_id=str(data.get('_document_id') or '').strip()
                if doc_id:
                    secret=(os.getenv('APP_SECRET') or '').encode('utf-8')
                    if not secret: raise RuntimeError('APP_SECRET não configurado')
                    token=hmac.new(secret,f'apr-public-signature:{int(doc_id)}'.encode('utf-8'),hashlib.sha256).hexdigest()[:40]
                    url=f'{base}/apr/{doc_id}/assinar-publico/{token}'
                    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=4,border=2)
                    qr.add_data(url); qr.make(fit=True)
                    qimg=qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
                    qbuf=io.BytesIO(); qimg.save(qbuf)
                    svg=fitz.open(stream=qbuf.getvalue(),filetype='svg')
                    qpdf=fitz.open('pdf',svg.convert_to_pdf())
                    page.show_pdf_page(fitz.Rect(page_w-84,6,page_w-24,66),qpdf,0)
                    qpdf.close(); svg.close()
                    page.insert_text((page_w-175,73),'QR geral de assinaturas',fontsize=5.5,fontname='helv')
            except Exception:
                pass
            y0=82
            # cabeçalho
            page.draw_rect(fitz.Rect(margin,y0,margin+name_w,y0+30),color=(.72,.70,.68),fill=(.94,.93,.92),width=.6)
            _fit_textbox(page,fitz.Rect(margin+4,y0+4,margin+name_w-4,y0+26),'Participante / Empresa',7,5.5,0,True)
            for j,d in enumerate(days):
                x=margin+name_w+j*day_w
                page.draw_rect(fitz.Rect(x,y0,x+day_w,y0+30),color=(.72,.70,.68),fill=(.94,.93,.92),width=.6)
                _fit_textbox(page,fitz.Rect(x+2,y0+3,x+day_w-2,y0+27),f'{day_names[d.weekday()]}\n{d.strftime("%d/%m")}',7,5.4,1,True)
            for local_i,w in enumerate(workers[start_idx:start_idx+rows_per_page]):
                y=y0+30+local_i*row_h
                page.draw_rect(fitz.Rect(margin,y,margin+name_w,y+row_h),color=(.80,.78,.76),width=.5)
                label=(w.get('worker') or w.get('name') or '')
                if w.get('company'): label += '\n'+str(w.get('company'))
                if w.get('role'): label += '\n'+str(w.get('role'))
                _fit_textbox(page,fitz.Rect(margin+4,y+4,margin+name_w-4,y+row_h-4),label,7,5.2,0,False)
                daily=w.get('daily_signatures') if isinstance(w.get('daily_signatures'),dict) else {}
                for j,d in enumerate(days):
                    x=margin+name_w+j*day_w
                    cell=fitz.Rect(x,y,x+day_w,y+row_h)
                    page.draw_rect(cell,color=(.80,.78,.76),width=.5)
                    item=daily.get(d.isoformat()) if isinstance(daily,dict) else None
                    if not isinstance(item,dict): continue
                    sig_rect=fitz.Rect(x+5,y+4,x+day_w-5,y+row_h-17)
                    if not _add_signature(page,sig_rect,item.get('signature_image'),stamp=False):
                        _fit_textbox(page,sig_rect,'ASSINADO',6.2,5.0,1,True)
                    stamp=str(item.get('signed_by_name') or '')[:22]+'\n'+str(item.get('signed_at') or item.get('date') or '')
                    if stamp:
                        _fit_textbox(page,fitz.Rect(x+2,y+row_h-16,x+day_w-2,y+row_h-3),stamp,5.2,4.2,1,False)
            page.insert_text((margin,page_h-16),'Cada rubrica diária é vinculada ao usuário participante e à data real do registro.',fontsize=6,fontname='helv')


def generate_apr(data: dict, out_pdf: Path):
    template=TEMPLATE_DIR/'APR - Modelo em branco.pdf'
    source=fitz.open(template)
    if source.page_count != 3: raise RuntimeError('O modelo da APR deve ter 3 páginas.')
    steps=list(data.get('steps',[]) or [])[:20]
    risk_pages=max(1,(len(steps)+4)//5)
    # A página 1 do modelo comporta 5 etapas. Para APRs maiores, repetimos essa página
    # mantendo exatamente o mesmo layout e depois anexamos checklist e equipe.
    doc=fitz.open()
    for _ in range(risk_pages): doc.insert_pdf(source,from_page=0,to_page=0)
    doc.insert_pdf(source,from_page=1,to_page=2)
    source.close()
    for i in range(risk_pages): _header_apr(doc[i],data,0)
    _header_apr(doc[risk_pages],data,1)
    _header_apr(doc[risk_pages+1],data,2)
    xs=[17,151.7,245.7,438.7,478.7,797]; ys=[121.8,182.9,273.7,335.9,423.7,508.1]
    general_severity=_severity_code(data.get('severity',''))
    for page_idx in range(risk_pages):
        p=doc[page_idx]
        for r,item in enumerate(steps[page_idx*5:(page_idx+1)*5]):
            for c,key in enumerate(['stage','hazard','risk','severity','control']):
                pad=3.2 if c!=3 else 1.0
                rect=fitz.Rect(xs[c]+pad,ys[r]+3,xs[c+1]-pad,ys[r+1]-3)
                value=item.get(key,'')
                # Se a etapa estiver preenchida e não tiver severidade individual, usa a severidade geral
                # da APR. Assim a coluna SEVERIDADE nunca fica vazia por acidente no PDF.
                if key=='severity':
                    value=_severity_code(value) or (general_severity if any((item.get('stage'),item.get('hazard'),item.get('risk'),item.get('control'))) else '')
                _fit_textbox(p,rect,value,6.4 if c!=3 else 8.0,4.2,1 if c==3 else 0,c==3)
    p=doc[risk_pages]
    try:
        p.draw_rect(fitz.Rect(705,523,839,535.5),color=(1,1,1),fill=(1,1,1),overlay=True)
        _fit_textbox(p,fitz.Rect(705,523,839,535.5),'RUBRICA',6.5,5.5,1,True)
    except Exception: pass
    _fit_textbox(p,fitz.Rect(93,108,162,120),data.get('leader_phone',''),5.7)
    _fit_textbox(p,fitz.Rect(75,120,162,132),data.get('sst_phone',''),5.7)
    _fit_textbox(p,fitz.Rect(73,132,162,144),data.get('radio_channel',''),5.7)
    critical, permits=_critical_activity_summary(data)
    _fit_textbox(p,fitz.Rect(22,144,162,151.5),f'Atividade crítica: {critical}',4.9,4.2,0,True)
    if critical=='SIM' and permits:
        _fit_textbox(p,fitz.Rect(22,151,162,161),f'PTs: {permits}',4.3,3.7,0,False)
    y0,step=194.9,9.65; centers={'SIM':560.8,'NÃO':602.5,'NAO':602.5,'N/A':644.2}
    for i in range(24):
        ans=str((data.get('checklist') or ['']*24)[i] if i<len(data.get('checklist',[])) else '').upper().strip(); x=centers.get(ans)
        if x: p.insert_text((x-2,y0+i*step+7.2),'X',fontsize=7.2,fontname='hebo')
    ay=[460.5,474.4,488.2,502.1,516.0,529.8]; ax=[17,167.9,280.2,539.9,665.1]
    for i,item in enumerate(data.get('approvals',[])[:5]):
        _fit_textbox(p,fitz.Rect(ax[0]+3,ay[i]+1.5,ax[1]-3,ay[i+1]-1.5),item.get('name',''),5.8,4.3,1)
        _fit_textbox(p,fitz.Rect(ax[1]+3,ay[i]+1.5,ax[2]-3,ay[i+1]-1.5),item.get('role',''),5.8,4.3,1)
        period=f"{item.get('start','')} ate {item.get('end','')}" if item.get('start') or item.get('end') else ''
        _fit_textbox(p,fitz.Rect(ax[2]+3,ay[i]+1.5,ax[3]-3,ay[i+1]-1.5),period,5.8,4.3,1)
        rect=fitz.Rect(ax[3]+4,ay[i]+2,ax[4]-4,ay[i+1]-2)
        if not _add_item_signature(p,rect,item): _fit_textbox(p,rect,item.get('signature',''),5.8,4.3,1)
    p=doc[risk_pages+1]
    _fit_textbox(p,fitz.Rect(154,151,276,170),data.get('leader_phone',''),9)
    _fit_textbox(p,fitz.Rect(125,170,276,189),data.get('sst_phone',''),9)
    _fit_textbox(p,fitz.Rect(123,189,276,208),data.get('radio_channel',''),9)
    critical, permits=_critical_activity_summary(data)
    _fit_textbox(p,fitz.Rect(25,210,276,225),f'ATIVIDADE CRÍTICA: {critical}',8.0,6.0,0,True)
    if critical=='SIM' and permits:
        _fit_textbox(p,fitz.Rect(25,225,276,254),f'Permissões: {permits}',7.2,5.0,0,False)
    wx=[17,283.8,823.8,941.5,1162.7]; wy=[303.2+17.06*i for i in range(25)]
    # Uma linha por trabalhador + uma linha extra para cada dia posterior já assinado
    # (rubricas diárias), para que todas as assinaturas apareçam também na página principal.
    from datetime import datetime as _dt
    _rows=[]
    for _w in (data.get('workers',[]) or []):
        _rows.append(_w)
        _daily=_w.get('daily_signatures') if isinstance(_w.get('daily_signatures'),dict) else {}
        for _iso in sorted(_daily):
            _it=_daily[_iso]
            if not isinstance(_it,dict) or not _it.get('signature_image'): continue
            try: _br=_dt.strptime(str(_iso)[:10],'%Y-%m-%d').strftime('%d/%m/%Y')
            except Exception: continue
            if _br==str(_w.get('date') or '') and _w.get('signature_image')==_it.get('signature_image'): continue
            if _br==str(_w.get('date') or ''): continue
            _rows.append({'company':_w.get('company',''),'worker':_w.get('worker') or _w.get('name',''),'date':_br,'signature_image':_it.get('signature_image'),'signature':''})
    for i,item in enumerate(_rows[:24]):
        for c,val in enumerate([item.get('company',''),item.get('worker',''),item.get('date','')]):
            _fit_textbox(p,fitz.Rect(wx[c]+5,wy[i]+2,wx[c+1]-5,wy[i+1]-2),val,8.6 if c!=1 else 8.2,6,1)
        rect=fitz.Rect(wx[3]+5,wy[i]+2,wx[4]-5,wy[i+1]-2)
        if not _add_item_signature(p,rect,item): _fit_textbox(p,rect,item.get('signature',''),8,6,1)
    _append_apr_daily_signatures(doc,data)
    return _publish(doc,out_pdf)


def generate_pt_height(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/'PT - Modelo em branco.pdf')
    if len(doc)<2: raise RuntimeError('O modelo da PT precisa ter 2 páginas.')
    def put(page,rect,text,size=7,align=0,bold=False):
        if text: _fit_textbox(page,fitz.Rect(*rect),str(text),size,4.5,align,bold)
    p1=doc[0]
    put(p1,(65,103,295,118),data.get('cluster','')); put(p1,(328,103,565,118),data.get('site',''))
    put(p1,(55,124,295,139),data.get('base','')); put(p1,(357,124,565,139),data.get('contractor',''))
    put(p1,(35,212,565,226),data.get('activity',''),6.5)
    type_x={'Andaime':31.5,'Escada':90.5,'Cesto Aéreo':145.5,'PEMT':218.5,'Escalada TME':266.5,'Escalada Aerogerador':345.5,'Escalada RMT/LT':455.5,'Outro':542.5}
    work_type_map={
        'Uso de andaime':'Andaime',
        'Uso de escada':'Escada',
        'Plataforma elevatória (PTA)':'PEMT',
        'Plataforma elevatória (PEMT)':'PEMT',
        'Cesto Aéreo':'Cesto Aéreo',
        'Escalada TME':'Escalada TME',
        'Escalada Aerogerador':'Escalada Aerogerador',
        'Escalada RMT/LT':'Escalada RMT/LT',
        'Andaime':'Andaime','Escada':'Escada','PEMT':'PEMT','Outro':'Outro',
    }
    other_types=[]
    marked=set()
    for raw in data.get('work_types',[]):
        t=str(raw or '').strip()
        mapped=work_type_map.get(t)
        if mapped:
            if mapped not in marked:
                p1.insert_text((type_x[mapped],194),'X',fontsize=7,fontname='hebo')
                marked.add(mapped)
        elif t:
            other_types.append(t)
    if other_types:
        if 'Outro' not in marked:
            p1.insert_text((type_x['Outro'],194),'X',fontsize=7,fontname='hebo')
        # Registra no próprio PDF quais opções adicionais da tela foram marcadas.
        _fit_textbox(p1,fitz.Rect(420,201,565,211),', '.join(other_types),4.2,3.2,0,False)
    row_y=[262,279,298,324,349,363,389,414,428,447,466,481,495,509,523,537,552]; ans_x={'SIM':501.5,'NÃO':529.5,'N/A':558}
    for y,a in zip(row_y,data.get('checklist',[])):
        if a in ans_x: p1.insert_text((ans_x[a],y),'X',fontsize=7.5,fontname='hebo')
    p2=doc[1]; worker_rows=[(112,128),(129,146),(147,163),(164,181),(182,198)]
    for w,(y0,y1) in zip(data.get('workers',[])[:5],worker_rows):
        put(p2,(32,y0+2,266,y1-1),w.get('name',''),6.5); put(p2,(272,y0+2,380,y1-1),w.get('company',''),6.5)
        _add_signature(p2,fitz.Rect(386,y0+1,570,y1-1),w.get('signature_image'))
    put(p2,(34,234,568,276),data.get('comments',''),7)
    put(p2,(92,312,160,327),data.get('open_date',''),5.8,2); put(p2,(224,312,301,327),data.get('open_time',''),5.8,2)
    put(p2,(378,312,436,327),data.get('close_date',''),5.8,2); put(p2,(512,312,571,327),data.get('close_time',''),5.8,2)
    put(p2,(31,345,160,383),data.get('open_name',''),7,1); put(p2,(307,345,437,383),data.get('close_name',''),7,1)
    _add_signature(p2,fitz.Rect(165,344,302,384),data.get('open_signature_image')); _add_signature(p2,fitz.Rect(441,344,572,384),data.get('close_signature_image'))
    p2.insert_text((455,805),data.get('code',''),fontsize=5.5,fontname='helv')
    return _publish(doc,out_pdf)


def generate_confined(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/'PET Espaco Confinado - Modelo.pdf')
    def put(page,rect,text,size=7,align=0,bold=False):
        if text: _fit_textbox(page,fitz.Rect(*rect),str(text),size,4.5,align,bold)
    p1=doc[0]
    put(p1,(62,103,315,116),data.get('cluster','')); put(p1,(351,103,568,116),data.get('site',''))
    put(p1,(55,124,315,138),data.get('base','')); put(p1,(370,124,568,138),data.get('contractor',''))
    xy={'Fundação - Turbina Eólica':(33.8,191.5),'HUB - Turbina Eólica':(155,191.5),'Pá - Turbina Eólica':(254.5,191.5),'Caixa Separadora de Óleo':(353,191.5),'Unidade Geradora - UG':(481,191.5)}
    for t in data.get('entry_types',[]):
        if t in xy: p1.insert_text(xy[t],'X',fontsize=7.5,fontname='hebo')
    put(p1,(34,214,568,235),data.get('activity',''),6.5)
    ys=[269,283,302,321,335,349,364,378,449,463,477,492,506,520,534]; xs={'SIM':505,'NÃO':534,'N/A':563}
    for y,a in zip(ys,data.get('checklist',[])):
        if a in xs: p1.insert_text((xs[a],y),'X',fontsize=7.5,fontname='hebo')
    # A tela coleta O2, inflamáveis, CO e H2S. O modelo Serena possui três
    # linhas: O2, inflamáveis e gases/vapores tóxicos. CO e H2S são reunidos
    # na terceira linha para que nenhuma leitura seja perdida no PDF.
    read_x=[(221,304),(306,396),(398,489),(490,574)]
    readings=data.get('air_readings') or {}
    for key,y0,y1 in (('o2',399,413),('lii',414,427)):
        vals=readings.get(key) or []
        for rect,val in zip(read_x,vals): put(p1,(rect[0],y0,rect[1],y1),val,6.3,1)
    co=readings.get('co') or []; h2s=readings.get('h2s') or []
    toxic=[]
    for idx in range(4):
        cv=str(co[idx] if idx<len(co) else '').strip(); hv=str(h2s[idx] if idx<len(h2s) else '').strip()
        parts=[]
        if cv: parts.append(f'CO {cv}')
        if hv: parts.append(f'H2S {hv}')
        toxic.append(' / '.join(parts))
    for rect,val in zip(read_x,toxic): put(p1,(rect[0],429,rect[1],441),val,5.0,1)
    p2=doc[1]
    for r,key in zip(((76,89,160,102),(204,89,298,102),(349,89,437,102),(494,89,568,102)),('open_date','open_time','close_date','close_time')): put(p2,r,data.get(key,''),6,1)
    name_rects={'open_supervisor_name':(33,122,160,155),'close_supervisor_name':(306,122,438,155),'open_vigia_name':(33,178,160,219),'close_vigia_name':(306,178,438,219)}
    for k,r in name_rects.items(): put(p2,r,data.get(k,''),7,1)
    sig_rects={'open_supervisor_signature_image':(164,121,301,155),'close_supervisor_signature_image':(442,121,568,155),'open_vigia_signature_image':(164,178,301,219),'close_vigia_signature_image':(442,178,568,219)}
    for k,r in sig_rects.items(): _add_signature(p2,fitz.Rect(*r),data.get(k))
    rows=[(270,291),(292,313),(314,335),(336,357),(358,379),(380,391)]
    for w,(y0,y1) in zip(data.get('workers',[])[:6],rows):
        put(p2,(34,y0,272,y1),w.get('name',''),6.5); put(p2,(274,y0,386,y1),w.get('company',''),6.5); _add_signature(p2,fitz.Rect(389,y0,568,y1),w.get('signature_image'))
    put(p2,(34,409,568,448),data.get('comments',''),6.5); p2.insert_text((485,805),data.get('code',''),fontsize=5.5,fontname='helv')
    return _publish(doc,out_pdf)


def generate_electrical_like(kind: str, data: dict, out_pdf: Path):
    cfg=MODULES[kind]; doc=fitz.open(TEMPLATE_DIR/cfg['template'])
    def put(page,rect,text,size=7,align=0,bold=False):
        if text: _fit_textbox(page,fitz.Rect(*rect),str(text),size,4.5,align,bold)
    p1=doc[0]
    put(p1,(62,118,299,137),data.get('cluster','')); put(p1,(326,118,569,137),data.get('site',''))
    put(p1,(53,139,299,158),data.get('base','')); put(p1,(353,139,569,158),data.get('contractor','')); put(p1,(124,176,569,197),data.get('activity',''),6.5)
    ys=[238.8,258.3,277.4,291.3,305.6,319.8,334.1,348.3,362.7,382.2,401.7,415.9,430.2,450.8,471.5,485.7] if kind=='electrical' else [238.8,258.3,277.4,291.3,305.6,319.8,334.1,348.3,362.7,376.9,391.2,405.5,419.7,434.0,448.2,461.8,476.0]
    xs={'SIM':505,'NÃO':534,'N/A':563}
    for y,a in zip(ys,data.get('checklist',[])):
        if a in xs: p1.insert_text((xs[a],y),'X',fontsize=7.5,fontname='hebo')
    p2=doc[1]
    for r,key in zip(((76,89,160,102),(204,89,298,102),(349,89,437,102),(494,89,568,102)),('open_date','open_time','close_date','close_time')): put(p2,r,data.get(key,''),6,1)
    put(p2,(33,122,160,160),data.get('open_responsible_name',''),7,1); put(p2,(306,122,438,160),data.get('close_responsible_name',''),7,1)
    _add_signature(p2,fitz.Rect(164,121,301,160),data.get('open_responsible_signature_image')); _add_signature(p2,fitz.Rect(442,121,568,160),data.get('close_responsible_signature_image'))
    rows=[(214,234),(236,255),(257,276),(278,297),(299,318),(320,337)] if kind=='electrical' else [(208,228),(230,249),(251,270),(272,291),(293,312),(314,325)]
    for w,(y0,y1) in zip(data.get('workers',[])[:6],rows):
        put(p2,(34,y0,272,y1),w.get('name',''),6.5); put(p2,(274,y0,386,y1),w.get('company',''),6.5); _add_signature(p2,fitz.Rect(389,y0,568,y1),w.get('signature_image'))
    put(p2,(34,356,568,398) if kind=='electrical' else (34,343,568,385),data.get('comments',''),6.5); p2.insert_text((485,805),data.get('code',''),fontsize=5.5,fontname='helv')
    return _publish(doc,out_pdf)


def generate_standard(kind: str, data: dict, out_pdf: Path):
    cfg=MODULES[kind]; doc=fitz.open(TEMPLATE_DIR/cfg['template'])
    def put(page,rect,text,size=7,align=0,bold=False):
        if text: _fit_textbox(page,fitz.Rect(*rect),str(text),size,4.5,align,bold)
    p1=doc[0]
    put(p1,(62,118,299,137),data.get('cluster','')); put(p1,(326,118,569,137),data.get('site','')); put(p1,(53,139,299,158),data.get('base','')); put(p1,(353,139,569,158),data.get('contractor',''))
    if cfg.get('equipment_mode')=='multi':
        for opt in data.get('equipment_types',[]):
            pt=cfg.get('equipment_marks',{}).get(opt)
            if pt: p1.insert_text(pt,'X',fontsize=8,fontname='hebo')
    elif cfg.get('equipment_mode')=='text': put(p1,cfg['equipment_rect'],data.get('equipment_type',''),6.5)
    put(p1,cfg['activity_rect'],data.get('activity',''),6.5)
    xs={'SIM':504,'NÃO':532.5,'N/A':561}
    for y,a in zip(cfg['check_ys'],data.get('checklist',[])):
        if a in xs: p1.insert_text((xs[a],y),'X',fontsize=7.5,fontname='hebo')
    p2=doc[1]
    if cfg.get('p2_variant')=='suppression':
        date_rects=((76,96,160,109),(204,96,298,109),(349,96,437,109),(494,96,568,109)); name_rects=((33,129,160,169),(306,129,438,169)); sig_rects=((164,129,301,169),(442,129,568,169)); rows=[(215,236),(237,257),(258,278),(279,299),(300,319)]; comments=(34,355,568,397)
    else:
        date_rects=((76,89,160,102),(204,89,298,102),(349,89,437,102),(494,89,568,102)); name_rects=((33,120,160,163),(306,120,438,163)); sig_rects=((164,120,301,163),(442,120,568,163)); rows=[(211,232),(233,253),(254,274),(275,295),(296,316)]; comments=(34,351,568,392)
    for r,key in zip(date_rects,('open_date','open_time','close_date','close_time')): put(p2,r,data.get(key,''),6,1)
    put(p2,name_rects[0],data.get('open_responsible_name',''),7,1); put(p2,name_rects[1],data.get('close_responsible_name',''),7,1)
    _add_signature(p2,fitz.Rect(*sig_rects[0]),data.get('open_responsible_signature_image')); _add_signature(p2,fitz.Rect(*sig_rects[1]),data.get('close_responsible_signature_image'))
    for w,(y0,y1) in zip(data.get('workers',[])[:5],rows):
        put(p2,(34,y0,272,y1),w.get('name',''),6.5); put(p2,(274,y0,386,y1),w.get('company',''),6.5); _add_signature(p2,fitz.Rect(389,y0,568,y1),w.get('signature_image'))
    put(p2,comments,data.get('comments',''),6.5); p2.insert_text((485,805),data.get('code',''),fontsize=5.5,fontname='helv')
    return _publish(doc,out_pdf)


def generate_vehicle(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/'Checklist Veiculo Pesado - Modelo.pdf')
    while len(doc)>1: doc.delete_page(len(doc)-1)
    p=doc[0]
    def put(rect,text,size=6,align=0):
        if text: _fit_textbox(p,fitz.Rect(*rect),str(text),size,4.5,align)
    put((62,52,272,65),data.get('cluster',''),6.2); put((309,52,488,65),data.get('site',''),6.2); put((538,52,641,65),data.get('model',''),6.2); put((121,68,274,81),data.get('operator',''),6.2); put((674,52,707,65),data.get('month',''),6.2,1)
    year=str(data.get('year','')); put((751,52,780,65),year[-2:] if len(year)>=2 else year,6.2,1)
    answer_x=[{'C':291,'NC':315,'NA':339},{'C':363,'NC':387,'NA':411},{'C':435,'NC':460,'NA':484},{'C':508,'NC':532,'NA':556},{'C':580,'NC':604,'NA':629},{'C':653,'NC':677,'NA':701},{'C':725,'NC':749,'NA':773}]
    row_y=[114,128,147,165,180,194,208,222,235,249,263,276,290,303,317,330]
    visto=[(279,331,350,349),(352,331,422,349),(424,331,494,349),(497,331,567,349),(569,331,639,349),(642,331,712,349),(714,331,783,349)]
    for di,day in enumerate(VEHICLE_DAYS):
        dd=(data.get('days') or {}).get(day,{})
        for ri,a in enumerate((dd.get('answers') or [])[:len(row_y)]):
            x=answer_x[di].get(a)
            if x is not None: p.insert_text((x-2.6,row_y[ri]),'X',fontsize=7.2,fontname='hebo')
        if not _add_signature(p,fitz.Rect(*visto[di]),dd.get('signature_image')) and dd.get('visto') and dd.get('visto')!='RUBRICA': put(visto[di],dd.get('visto'),5,1)
    put((18,380,780,420),data.get('observations',''),6.2)
    # Anexos fotográficos do veículo pesado: até 3 fotos por item/dia.
    for di,day in enumerate(VEHICLE_DAYS):
        dd=(data.get('days') or {}).get(day,{}) or {}
        for ii,item_photos in enumerate(dd.get('photos') or []):
            rows=item_photos if isinstance(item_photos,list) else []
            for photo_no,rel in enumerate(rows[:3],1):
                photo=_sig_abs(rel)
                if not photo: continue
                page=doc.new_page(width=595.28,height=841.89)
                page.insert_text((42,55),'ANEXO — EVIDÊNCIA FOTOGRÁFICA',fontsize=15,fontname='hebo')
                page.insert_text((42,79),f'Veículo Pesado · {day} · Item {VEHICLE_ITEM_NUMBERS[ii] if ii < len(VEHICLE_ITEM_NUMBERS) else ii+1} · Foto {photo_no}',fontsize=9.5,fontname='hebo')
                if ii < len(VEHICLE_CHECK_ITEMS):
                    page.insert_textbox(fitz.Rect(42,96,553,155),str(VEHICLE_CHECK_ITEMS[ii]),fontsize=9,fontname='helv')
                box=fitz.Rect(42,170,553,790)
                try:
                    pix=fitz.Pixmap(str(photo)); ratio=min(box.width/max(pix.width,1),box.height/max(pix.height,1)); w=pix.width*ratio; h=pix.height*ratio
                    rect=fitz.Rect(box.x0+(box.width-w)/2,box.y0,box.x0+(box.width+w)/2,box.y0+h)
                    page.insert_image(rect,filename=str(photo),keep_proportion=True)
                except Exception: page.insert_textbox(box,'Foto registrada, mas não foi possível renderizá-la.',fontsize=9,fontname='helv',align=1)
    return _publish(doc,out_pdf)



def _grid_centers(bounds):
    return [(bounds[i]+bounds[i+1])/2 for i in range(len(bounds)-1)]


def _draw_mark(page, x, y):
    page.insert_text((x-2.8,y+2.5),'X',fontsize=7.2,fontname='hebo',color=(0,0,0))


def _periodic_answer_x(bounds, period_index, answer):
    centers=_grid_centers(bounds)
    offset=period_index*3
    idx={'C':0,'NC':1,'NA':2}.get(answer)
    return centers[offset+idx] if idx is not None and offset+idx < len(centers) else None


def generate_hoist(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/INSPECTION_MODULES['hoist']['template'])
    p1,p2=doc[0],doc[1]
    _fit_textbox(p1,fitz.Rect(72,84,250,98),data.get('cluster_site',''),6.2,4.8)
    _fit_textbox(p1,fitz.Rect(292,84,405,98),data.get('local',''),6.2,4.8)
    _fit_textbox(p1,fitz.Rect(420,84,610,98),data.get('turbine',''),6.2,4.8)
    _fit_textbox(p1,fitz.Rect(40,99,250,113),data.get('leader',''),6.2,4.8)
    _fit_textbox(p1,fitz.Rect(635,84,677,98),str(data.get('month','')),6,4.8,1)
    year=str(data.get('year','')); _fit_textbox(p1,fitz.Rect(700,84,744,98),year[-2:] if len(year)>=2 else year,6,4.8,1)
    xb=[250.8,271.7,295.1,319.9,343.3,368.0,390.6,415.4,437.2,461.9,486.7,511.4,536.1,560.9,585.6,610.3,635.0,656.4,677.7,700.4,723.1,744.5]
    yb1=[127.7,147.6,163.3,195.5,222.9,249.2,293.6,331.9,370.1,416.4,457.1,498.9]
    yb2=[40.3,82.2,124.1,166.0,187.2,220.7]
    periods=INSPECTION_MODULES['hoist']['periods']; pdata=data.get('periods') or {}
    for pi,name in enumerate(periods):
        info=pdata.get(name,{}) or {}
        x0=xb[pi*3]; x1=xb[pi*3+3]
        _replace_template_field(p1,(x0+1,114.3,x1-1,126.9),info.get('date',''),5.2,4.4,1)
        for ri,a in enumerate((info.get('answers') or [])[:11]):
            x=_periodic_answer_x(xb,pi,a)
            if x is not None: _draw_mark(p1,x,(yb1[ri]+yb1[ri+1])/2)
        for ri,a in enumerate((info.get('answers') or [])[11:16]):
            x=_periodic_answer_x(xb,pi,a)
            if x is not None: _draw_mark(p2,x,(yb2[ri]+yb2[ri+1])/2)
        _add_signature(p2,fitz.Rect(x0+3,231.7,x1-3,246.7),info.get('signature_image'))
    _fit_textbox(p2,fitz.Rect(17,271.8,744,298.3),data.get('observations',''),6.2,4.6)
    return _publish(doc,out_pdf)


def generate_light_vehicle(data: dict, out_pdf: Path):
    # O modelo legado tem cinco semanas, mas o formulário atual tem sete dias.
    # Use a grade diária completa, sem truncar sábado/domingo.
    if INSPECTION_MODULES['light_vehicle']['mode'] == 'daily':
        return generate_standard_checklist('light_vehicle', data, out_pdf)
    doc=fitz.open(TEMPLATE_DIR/INSPECTION_MODULES['light_vehicle']['template']); p=doc[0]
    fields=[((52,97,122,110),'cluster'),((147,97,212,110),'local'),((244,97,301,110),'vehicle'),((326,97,439,110),'plate'),((473,97,574,110),'company')]
    for r,k in fields: _fit_textbox(p,fitz.Rect(*r),data.get(k,''),5.5,4.2)
    xb=[234.9,257.5,280.0,302.6,325.1,347.7,370.3,392.8,415.8,438.3,460.9,483.5,506.4,528.6,551.1,574.1]
    yb=[137.7,155.9,170.7,185.4,200.2,214.9,229.7,244.5,259.2,274.0,288.8,303.5,318.3,333.0,347.8,362.6,377.3,392.1,406.8,421.6,436.4,451.1,465.9,480.7,495.4]
    periods=INSPECTION_MODULES['light_vehicle']['periods']; pdata=data.get('periods') or {}
    for pi,name in enumerate(periods):
        info=pdata.get(name,{}) or {}; x0=xb[pi*3]; x1=xb[pi*3+3]
        _replace_template_field(p,(x0+1,111.7,x1-1,124.7),info.get('date',''),5.0,4.2,1)
        for ri,a in enumerate((info.get('answers') or [])[:24]):
            x=_periodic_answer_x(xb,pi,a)
            if x is not None: _draw_mark(p,x,(yb[ri]+yb[ri+1])/2)
        _add_signature(p,fitz.Rect(x0+3,510.3,x1-3,531.5),info.get('signature_image'))
    row_bounds=[594.2,606.8,619.4,632.0,644.6,657.2]
    for i,row in enumerate((data.get('nonconformities') or [])[:5]):
        y0,y1=row_bounds[i],row_bounds[i+1]
        _fit_textbox(p,fitz.Rect(19,y0+1,71,y1-1),row.get('item',''),5.0,4.0,1)
        _fit_textbox(p,fitz.Rect(72,y0+1,438,y1-1),row.get('action',''),5.0,4.0)
        _fit_textbox(p,fitz.Rect(439,y0+1,506,y1-1),row.get('responsible',''),5.0,4.0,1)
        _replace_template_field(p,(507,y0+1,573,y1-1),row.get('date',''),4.8,4.0,1)
    return _publish(doc,out_pdf)


def generate_height_kit(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/INSPECTION_MODULES['height_kit']['template']); p=doc[0]
    fields=[((96,117,164,131),'site'),((194,117,297,131),'brand'),((334,117,498,131),'model'),((535,117,638,131),'company')]
    for r,k in fields: _fit_textbox(p,fitz.Rect(*r),data.get(k,''),5.8,4.4)
    _fit_textbox(p,fitz.Rect(663,117,703,131),str(data.get('month','')),5.6,4.3,1); year=str(data.get('year','')); _fit_textbox(p,fitz.Rect(726,117,767,131),year[-2:] if len(year)>=2 else year,5.6,4.3,1)
    xb=[297.6,317.2,339.5,363.0,385.4,408.9,430.4,453.9,474.7,498.2,521.7,545.2,568.8,592.3,615.8,639.3,662.9,683.1,703.4,724.9,746.4,767.0]
    yb=[159.1,178.1,210.5,237.9,264.5,288.1,311.6,335.1,362.1,387.5,408.7]
    periods=INSPECTION_MODULES['height_kit']['periods']; pdata=data.get('periods') or {}
    for pi,name in enumerate(periods):
        info=pdata.get(name,{}) or {}; x0=xb[pi*3]; x1=xb[pi*3+3]
        _replace_template_field(p,(x0+1,132.2,x1-1,145.7),info.get('date',''),5.0,4.2,1)
        for ri,a in enumerate((info.get('answers') or [])[:10]):
            x=_periodic_answer_x(xb,pi,a)
            if x is not None: _draw_mark(p,x,(yb[ri]+yb[ri+1])/2)
        _add_signature(p,fitz.Rect(x0+3,432.9,x1-3,457.7),info.get('signature_image'))
    _fit_textbox(p,fitz.Rect(74,481,767,507),data.get('observations',''),6.0,4.5)
    return _publish(doc,out_pdf)


def _serena_climber_header(page):
    """Marca Serena dentro da margem superior existente do modelo Climber.

    Não desloca nem cobre a tabela ou as coordenadas do formulário oficial.
    """
    brand = (0.835, 0.176, 0.196)
    page.insert_text((671, 23), 'SERENA', fontsize=18, fontname='hebo', color=brand, overlay=True)
    page.draw_line((670, 29), (755, 29), color=brand, width=1.6, overlay=True)


def generate_climber_assist(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/INSPECTION_MODULES['climber_assist']['template']); p1,p2=doc[0],doc[1]
    _serena_climber_header(p1)
    fields=[((157,87,758,102),'turbine'),((157,102,758,117),'responsible'),((157,117,758,132),'inspection_date'),((157,132,758,147),'model'),((157,147,758,163),'park')]
    for r,k in fields: _fit_textbox(p1,fitz.Rect(*r),data.get(k,''),6.0,4.6)
    rows=data.get('rows') or []
    p1_bounds=[221.5,266.5,311.5,356.5,401.5,435.6,469.7,514.7,582.8]
    p2_bounds=[29.6,74.6,131.2,165.3,210.3,255.3,300.3,345.3]
    answer_text={'ATENDE':'Atende','NAO_ATENDE':'Não atende','NA':'N/A'}
    def stamp(page,bounds,start_index):
        for local in range(len(bounds)-1):
            idx=start_index+local
            if idx>=len(rows): break
            row=rows[idx]; y0,y1=bounds[local],bounds[local+1]
            _fit_textbox(page,fitz.Rect(422,y0+3,493,y1-3),answer_text.get(row.get('answer',''),''),5.7,4.2,1,True if row.get('answer')=='NAO_ATENDE' else False)
            _fit_textbox(page,fitz.Rect(495,y0+3,630,y1-3),row.get('evidence',''),5.3,4.0)
            _fit_textbox(page,fitz.Rect(632,y0+3,758,y1-3),row.get('action',''),5.3,4.0)
    stamp(p1,p1_bounds,0); stamp(p2,p2_bounds,8)
    applicable=[r for r in rows if r.get('answer') in {'ATENDE','NAO_ATENDE'}]
    atende=sum(1 for r in applicable if r.get('answer')=='ATENDE'); nao=sum(1 for r in rows if r.get('answer')=='NAO_ATENDE'); na=sum(1 for r in rows if r.get('answer')=='NA')
    score=(100.0*atende/len(applicable)) if applicable else 0.0
    score_text=f'{score:.1f}%'.replace('.',',')
    _replace_template_field(p2,(420,377,493,397),score_text,8.0,6.0,1,True)
    _replace_template_field(p2,(494,377,758,397),f'{nao} não atende(m) | {na} não se aplica(m)',6.0,4.8,1,True)
    _add_signature(p2,fitz.Rect(170,401,405,432),data.get('signature_image'))
    _replace_template_field(p2,(452,402,610,430),data.get('inspection_date',''),6.2,4.8,1)
    # Fotos do Climber Assist ficam anexadas ao PDF oficial, vinculadas ao item.
    # Os caminhos já são persistidos em rows[i]['photos'] no salvamento.
    for item_index, row in enumerate(rows):
        for photo_index, relative_path in enumerate((row or {}).get('photos') or [], 1):
            photo = _sig_abs(relative_path)
            if not photo:
                continue
            try:
                pix = fitz.Pixmap(str(photo))
                if pix.width < 1 or pix.height < 1:
                    continue
                page = doc.new_page(width=595.28, height=841.89)
                page.insert_text((42, 55), 'ANEXO FOTOGRAFICO - CLIMBER ASSIST', fontsize=14, fontname='hebo')
                page.insert_text((42, 80), f'Item {item_index + 1} - Foto {photo_index}', fontsize=11, fontname='hebo')
                item = INSPECTION_MODULES['climber_assist']['items']
                if item_index < len(item):
                    page.insert_textbox(fitz.Rect(42, 96, 553, 150), str(item[item_index][0]), fontsize=9, fontname='helv')
                bounds = fitz.Rect(42, 160, 553, 790)
                ratio = min(bounds.width / pix.width, bounds.height / pix.height)
                width, height = pix.width * ratio, pix.height * ratio
                rect = fitz.Rect(bounds.x0 + (bounds.width - width) / 2,
                                 bounds.y0 + (bounds.height - height) / 2,
                                 bounds.x0 + (bounds.width + width) / 2,
                                 bounds.y0 + (bounds.height + height) / 2)
                page.insert_image(rect, filename=str(photo), keep_proportion=True)
            except Exception:
                # Foto inválida não impede gerar o restante da inspeção.
                continue
    return _publish(doc,out_pdf)


def generate_safety_belt(data: dict, out_pdf: Path):
    doc=fitz.open(TEMPLATE_DIR/INSPECTION_MODULES['safety_belt']['template']); p=doc[0]
    # Cabeçalho do formulário original Serena.
    _fit_textbox(p,fitz.Rect(60,58,350,70),data.get('unit',''),6.0,4.6)
    _fit_textbox(p,fitz.Rect(421,58,560,70),data.get('manufacturer',''),6.0,4.6)
    _fit_textbox(p,fitz.Rect(608,58,815,70),data.get('model',''),6.0,4.6)
    _fit_textbox(p,fitz.Rect(86,71,273,84),data.get('responsible',''),6.0,4.6)

    # 7 dias x C/NC/NA. Os limites abaixo vêm da grade do PDF original.
    xb=[273.95,296.51,322.19,349.31,374.99,402.11,426.95,454.09,478.09,505.21,532.33,559.45,586.57,613.69,640.84,667.96,695.08,718.48,741.64,766.72,791.56,815.22]
    yb=[106.58,127.34,151.70,179.30,199.37,236.69,253.37,277.37,300.05,335.23,356.47,373.75,395.83,419.83,442.06,466.06,495.46]
    periods=INSPECTION_MODULES['safety_belt']['periods']; pdata=data.get('periods') or {}
    for pi,name in enumerate(periods):
        info=pdata.get(name,{}) or {}; x0=xb[pi*3]; x1=xb[pi*3+3]
        _replace_template_field(p,(x0+1,83.0,x1-1,94.0),info.get('date',''),5.0,4.2,1)
        for ri,a in enumerate((info.get('answers') or [])[:16]):
            x=_periodic_answer_x(xb,pi,a)
            if x is not None: _draw_mark(p,x,(yb[ri]+yb[ri+1])/2)
        _add_signature(p,fitz.Rect(x0+3,495.2,x1-3,518.0),info.get('signature_image'))
    _fit_textbox(p,fitz.Rect(16,540,815,566),data.get('observations',''),6.0,4.5)
    return _publish(doc,out_pdf)


_FIELD_LABELS = {
    'cluster': 'Cluster', 'site': 'Site', 'base': 'Base', 'contractor': 'Contratada',
    'activity': 'Atividade', 'severity': 'Severidade geral', 'apr_date': 'Data da APR',
    'apr_valid_until': 'Validade até', 'apr_time': 'Hora', 'radio_channel': 'Canal de rádio',
    'leader_phone': 'Telefone líder', 'sst_phone': 'Telefone SST',
    'critical_activity': 'Atividade crítica', 'critical_permits': 'Permissões vinculadas',
    'open_date': 'Data de abertura', 'open_time': 'Hora de abertura',
    'close_date': 'Data de fechamento', 'close_time': 'Hora de fechamento',
    'comments': 'Comentários', 'observations': 'Observações',
    'model': 'Modelo', 'operator': 'Motorista/Operador', 'month': 'Mês', 'year': 'Ano',
    'equipment_type': 'Equipamento', 'equipment_types': 'Equipamentos',
    'work_types': 'Tipo de trabalho em altura', 'entry_types': 'Classificação do espaço confinado',
    'open_name': 'Responsável pela abertura', 'close_name': 'Responsável pelo fechamento',
    'open_responsible_name': 'Responsável pela abertura', 'close_responsible_name': 'Responsável pelo fechamento',
    'open_supervisor_name': 'Supervisor (abertura)', 'close_supervisor_name': 'Supervisor (fechamento)',
    'open_vigia_name': 'Vigia (abertura)', 'close_vigia_name': 'Vigia (fechamento)',
    'inspection_date': 'Data da inspeção', 'leader': 'Responsável pela inspeção',
    'park': 'Parque/Unidade', 'turbine': 'Aerogerador/Equipamento', 'cluster_site': 'Cluster/Site',
    'local': 'Local', 'vehicle': 'Veículo/Modelo', 'plate': 'Placa',
    'company':'Empresa', 'responsible':'Responsável / Autorizado LOTO', 'role':'Função',
    'aeg_number':'Nº AEG', 'manufacturer_model':'Fabricante / Modelo AEG',
    'loto_start_time':'Início LOTO', 'loto_end_time':'Conclusão LOTO',
    'work_description':'Descrição do trabalho',
    'loto_devices':'Dispositivos LOTO',
    'affected_workers':'Trabalhadores LOTO afetados', 'improvements':'Melhorias no LOTO',
    'improvements_answer':'Melhorias neste LOTO?', 'improvements_description':'Descrição das melhorias',
    'approver_name': 'Aprovador designado', 'revalidation_request_status': 'Status da revalidação',
}

_SIGNATURE_LABELS = [
    ('open_signature_image', 'Assinatura — abertura'),
    ('close_signature_image', 'Assinatura — fechamento'),
    ('open_responsible_signature_image', 'Assinatura — abertura'),
    ('close_responsible_signature_image', 'Assinatura — fechamento'),
    ('open_supervisor_signature_image', 'Assinatura — supervisor (abertura)'),
    ('close_supervisor_signature_image', 'Assinatura — supervisor (fechamento)'),
    ('open_vigia_signature_image', 'Assinatura — vigia (abertura)'),
    ('close_vigia_signature_image', 'Assinatura — vigia (fechamento)'),
    ('signature_image', 'Assinatura do responsável'),
]

_SKIP_SCALAR_KEYS = {
    'stop_time', 'operation_time',  # LOTO V36.18.86: ocultar campos removidos inclusive em documentos anteriores

    'code', 'status', 'kind', 'title', 'checklist', 'steps', 'workers', 'rows', 'periods', 'days',
    'nonconformities', 'approvals', 'linked_apr_id', 'linked_apr_code', 'linked_permit_name',
    'linked_permit_ids', 'air_readings', 'worker_count', 'worker_max', 'step_count',
    'apr_date_input', 'open_date_input', 'close_date_input', 'revalidation_requested_for_input',
    'improvements_answer', 'improvements_description', 'affected_workers', 'improvements',
} | {k for k, _ in _SIGNATURE_LABELS}


def _fallback_styles():
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors
    base = getSampleStyleSheet()
    return {
        'h1': ParagraphStyle('h1', parent=base['Heading1'], fontSize=16, spaceAfter=2, textColor='#181818'),
        'sub': ParagraphStyle('sub', parent=base['Normal'], fontSize=9, textColor='#4B4B4B', spaceAfter=10),
        'banner': ParagraphStyle('banner', parent=base['Normal'], fontSize=8.5, textColor='#8A6A00',
                                  backColor='#FFF3D6', borderPadding=6, spaceAfter=12),
        'h2': ParagraphStyle('h2', parent=base['Heading2'], fontSize=11, spaceBefore=10, spaceAfter=4, textColor='#D23532'),
        'cell': ParagraphStyle('cell', parent=base['Normal'], fontSize=8, leading=10, alignment=TA_LEFT),
        'header_cell': ParagraphStyle('header_cell', parent=base['Normal'], fontSize=8, leading=10, alignment=TA_LEFT, textColor=colors.white),
        'small': ParagraphStyle('small', parent=base['Normal'], fontSize=7.5, textColor='#4B4B4B'),
    }


def generate_fallback(kind: str, data: dict, out_pdf: Path):
    """PDF alternativo genérico, usado quando o arquivo-modelo oficial da
    Serena para este tipo de documento ainda não está em app/pdf_templates/.

    Não tenta reproduzir o layout oficial (isso exigiria coordenadas
    calibradas no arquivo real, que não temos) — em vez disso, lista os
    dados de forma clara e legível, deixando um aviso visível de que é um
    documento provisório. Assim que o PDF oficial for adicionado com o
    nome esperado, generate_document() volta a usar o gerador com
    coordenadas exatas automaticamente, sem precisar mudar mais nada.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    styles = _fallback_styles()
    story = []

    title = DOCUMENT_TITLES.get(kind, kind)
    if kind == 'loto':
        # Mesmo sistema de identidade visual do Climber Assist: assinatura
        # Serena em destaque no lado direito e linha de identificação vermelha.
        from reportlab.lib.styles import ParagraphStyle
        left_style = ParagraphStyle('serena_loto_depto', parent=styles['small'],
                                    fontSize=8, leading=11, textColor=colors.HexColor('#434343'))
        marca_style = ParagraphStyle('marca_serena_loto', parent=styles['h1'],
                                     fontSize=22, leading=25, alignment=2, spaceAfter=0)
        departamento = Paragraph('<b>GESTÃO DE ATIVOS · SAÚDE E SEGURANÇA DO TRABALHO</b>', left_style)
        marca = Paragraph('<font color="#D52D32"><b>SERENA</b></font>', marca_style)
        cabecalho = Table([[departamento, marca]], colWidths=[315, 165])
        cabecalho.setStyle(TableStyle([
            ('BOTTOMLINE', (0, 0), (-1, -1), 1.5, colors.HexColor('#D52D32')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(cabecalho)
        story.append(Spacer(1, 10))
    story.append(Paragraph(f"{title}", styles['h1']))
    story.append(Paragraph(f"Código: {data.get('code','')}", styles['sub']))
    if kind not in {'loto','safety_belt'}:
        story.append(Paragraph(
            "MODELO PROVISÓRIO — o layout oficial da Serena para este tipo de documento ainda não foi "
            "carregado no sistema. Este PDF traz os mesmos dados preenchidos, em um formato simples, até "
            "que o arquivo-modelo real seja adicionado.",
            styles['banner']))

    # --- Dados gerais: qualquer campo simples (texto/número) que não seja lista/dict ---
    linhas = []
    for key, value in data.items():
        if key in _SKIP_SCALAR_KEYS or value in (None, '', []):
            continue
        if isinstance(value, (dict, list)):
            if key in ('critical_permits', 'work_types', 'entry_types', 'equipment_types') and isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            else:
                continue
        label = _FIELD_LABELS.get(key, key.replace('_', ' ').capitalize())
        linhas.append([Paragraph(label, styles['cell']), Paragraph(str(value), styles['cell'])])
    if linhas:
        story.append(Paragraph('Dados gerais', styles['h2']))
        t = Table(linhas, colWidths=[130, 340])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EDE9E5')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # --- Etapas (APR) ---
    if data.get('steps'):
        story.append(Paragraph('Etapas · Perigos · Riscos', styles['h2']))
        header = [Paragraph(h, styles['header_cell']) for h in ('Etapa', 'Perigo', 'Risco', 'Severidade', 'Controle')]
        rows = [header]
        for s in data['steps']:
            if not any((s.get('stage'), s.get('hazard'), s.get('risk'), s.get('control'))):
                continue
            rows.append([Paragraph(str(s.get(k, '')), styles['cell']) for k in ('stage', 'hazard', 'risk', 'severity', 'control')])
        if len(rows) > 1:
            t = Table(rows, colWidths=[80, 90, 90, 55, 155])
            t.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9')),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#181818')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t)

    # --- Checklist (lista simples: APR ou PT) ---
    if data.get('checklist'):
        questions = CHECKLIST if kind == 'apr' else (MODULES.get(kind, {}).get('checklist') or [])
        story.append(Paragraph('Checklist', styles['h2']))
        rows = [[Paragraph('#', styles['header_cell']), Paragraph('Pergunta', styles['header_cell']), Paragraph('Resposta', styles['header_cell'])]]
        for i, answer in enumerate(data['checklist']):
            question = questions[i] if i < len(questions) else f'Item {i+1}'
            rows.append([Paragraph(str(i+1), styles['cell']), Paragraph(question, styles['cell']), Paragraph(answer or '—', styles['cell'])])
        t = Table(rows, colWidths=[20, 400, 60])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#181818')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    # --- Itens avulsos (inspeção em modo único: climber_assist e afins) ---
    if data.get('rows'):
        cfg_items = (INSPECTION_MODULES.get(kind, {}) or {}).get('items') or []
        answer_text = {'ATENDE': 'Atende', 'NAO_ATENDE': 'Não atende', 'NA': 'N/A'}
        story.append(Paragraph('Checklist', styles['h2']))
        rows = [[Paragraph(h, styles['header_cell']) for h in ('#', 'Item', 'Resposta', 'Ação corretiva')]]
        for i, row in enumerate(data['rows']):
            label = cfg_items[i][0] if i < len(cfg_items) else f'Item {i+1}'
            number = (cfg_items[i][1] if i < len(cfg_items) and len(cfg_items[i]) > 1 else str(i+1))
            rows.append([
                Paragraph(str(number), styles['cell']), Paragraph(label, styles['cell']),
                Paragraph(answer_text.get(row.get('answer',''), row.get('answer','') or '—'), styles['cell']),
                Paragraph(row.get('action','') or '', styles['cell']),
            ])
        t = Table(rows, colWidths=[18, 260, 70, 132])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#181818')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    # --- Períodos (inspeção multi-período: Talha, Veículo Leve, Kit de Altura) ---
    if data.get('periods'):
        cfg_items = (INSPECTION_MODULES.get(kind, {}) or {}).get('items') or []
        story.append(Paragraph('Checklist por período', styles['h2']))
        for name, info in data['periods'].items():
            if not info or not any(info.get('answers') or []):
                continue
            story.append(Paragraph(f"{name} — {info.get('date','sem data')}", styles['small']))
            rows = [[Paragraph(h, styles['cell']) for h in ('#', 'Item', 'Resposta')]]
            for i, ans in enumerate(info.get('answers') or []):
                label = cfg_items[i][0] if i < len(cfg_items) else f'Item {i+1}'
                number = (cfg_items[i][1] if i < len(cfg_items) and len(cfg_items[i]) > 1 else str(i+1))
                rows.append([Paragraph(str(number), styles['cell']), Paragraph(label, styles['cell']), Paragraph(ans or '—', styles['cell'])])
            t = Table(rows, colWidths=[18, 380, 82])
            t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9'))]))
            story.append(t)
            story.append(Spacer(1, 6))

    # --- Dias (Veículo Pesado) ---
    if data.get('days'):
        story.append(Paragraph('Checklist por dia', styles['h2']))
        for day in VEHICLE_DAYS:
            info = (data['days'] or {}).get(day) or {}
            if not any(info.get('answers') or []):
                continue
            story.append(Paragraph(day, styles['small']))
            rows = [[Paragraph(str(i+1), styles['cell']), Paragraph(a or '—', styles['cell'])] for i, a in enumerate(info.get('answers') or [])]
            t = Table(rows, colWidths=[18, 462])
            t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9'))]))
            story.append(t)
            story.append(Spacer(1, 6))

    # --- Equipe / Parte 2 LOTO ---
    if data.get('workers'):
        if kind=='loto':
            story.append(Paragraph('Parte 2 — Trabalhadores LOTO Afetados', styles['h2']))
            rows = [[Paragraph(h, styles['header_cell']) for h in ('Nome', 'Empresa', 'Função', 'Horário', 'Assinatura')]]
            for w in data['workers']:
                if not any((w.get('worker'), w.get('company'), w.get('role'), w.get('time'), w.get('signature_image'))):
                    continue
                sig_cell=Paragraph('Sem assinatura', styles['small'])
                sig_path=_sig_abs(w.get('signature_image'))
                if sig_path:
                    try: sig_cell=Image(str(sig_path), width=72, height=28)
                    except Exception: pass
                rows.append([
                    Paragraph(w.get('worker') or '', styles['cell']),
                    Paragraph(w.get('company') or '', styles['cell']),
                    Paragraph(w.get('role') or '', styles['cell']),
                    Paragraph(w.get('time') or '', styles['cell']),
                    sig_cell,
                ])
            if len(rows)>1:
                t=Table(rows,colWidths=[118,92,92,48,130])
                t.setStyle(TableStyle([
                    ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#E3DFD9')),
                    ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#181818')),
                    ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                    ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                    ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                    ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
                ]))
                story.append(t)
        else:
            story.append(Paragraph('Equipe', styles['h2']))
            rows = [[Paragraph(h, styles['header_cell']) for h in ('Nome', 'Empresa', 'Função/Assinatura')]]
            for w in data['workers']:
                if not any((w.get('name') or w.get('worker'), w.get('company'))):
                    continue
                assinado = 'Assinado' if w.get('signature_image') else 'Sem assinatura'
                rows.append([
                    Paragraph(w.get('name') or w.get('worker') or '', styles['cell']),
                    Paragraph(w.get('company', ''), styles['cell']),
                    Paragraph(f"{w.get('role','')} · {assinado}".strip(' ·'), styles['cell']),
                ])
            if len(rows) > 1:
                t = Table(rows, colWidths=[180, 150, 140])
                t.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E3DFD9')),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#181818')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ]))
                story.append(t)

    sig_flowables = []
    for key, label in _SIGNATURE_LABELS:
        path = _sig_abs(data.get(key))
        if not path:
            continue
        try:
            img = Image(str(path), width=120, height=45)
            sig_flowables.append(KeepTogether([Paragraph(label, styles['small']), img, Spacer(1, 8)]))
        except Exception:
            continue
    if sig_flowables:
        story.append(Paragraph('Assinaturas', styles['h2']))
        story.extend(sig_flowables)

    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4,
                             leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    doc.build(story)

    # Fotos salvas nos itens de inspeção: anexa imagens ao próprio PDF,
    # sem exigir foto para finalizar e sem modificar os arquivos originais.
    if kind in INSPECTION_MODULES:
        photo_entries = []
        if isinstance(data.get('rows'), list):
            for i, row in enumerate(data['rows']):
                for j, rel in enumerate((row or {}).get('photos') or []):
                    photo_entries.append((f'Item {i+1} - Foto {j+1}', rel))
        if isinstance(data.get('periods'), dict):
            for period, info in data['periods'].items():
                for i, photos in enumerate((info or {}).get('photos') or []):
                    for j, rel in enumerate(photos or []):
                        photo_entries.append((f'{period} - Item {i+1} - Foto {j+1}', rel))
        if isinstance(data.get('days'), dict):
            for day, info in data['days'].items():
                for i, photos in enumerate((info or {}).get('photos') or []):
                    for j, rel in enumerate(photos or []):
                        photo_entries.append((f'{day} - Item {i+1} - Foto {j+1}', rel))
        if photo_entries:
            pdf = fitz.open(out_pdf)
            added = 0
            for label, rel in photo_entries:
                photo = _sig_abs(rel)
                if not photo:
                    continue
                try:
                    pix = fitz.Pixmap(str(photo))
                    if pix.width < 1 or pix.height < 1:
                        continue
                    page = pdf.new_page(width=595.28, height=841.89)
                    page.insert_text((42, 55), 'ANEXO FOTOGRAFICO', fontsize=16, fontname='hebo', color=(.82,.16,.18))
                    page.insert_text((42, 80), f'{kind.upper()} - {label}', fontsize=10, fontname='helv')
                    box = fitz.Rect(42, 105, 553, 790)
                    ratio = min(box.width/pix.width, box.height/pix.height)
                    width, height = pix.width*ratio, pix.height*ratio
                    rect = fitz.Rect(box.x0+(box.width-width)/2, box.y0+(box.height-height)/2,
                                     box.x0+(box.width+width)/2, box.y0+(box.height+height)/2)
                    page.insert_image(rect, filename=str(photo), keep_proportion=True)
                    added += 1
                except Exception:
                    continue
            if added:
                tmp = out_pdf.with_name(out_pdf.stem + '_photos_tmp.pdf')
                pdf.save(tmp, garbage=4, deflate=True)
                pdf.close()
                tmp.replace(out_pdf)
            else:
                pdf.close()
    return out_pdf


def _expected_template_path(kind: str) -> Path | None:
    """Caminho do PDF-modelo oficial que cada tipo de documento espera.
    Usado só para checar se o arquivo real já existe antes de decidir
    entre o gerador oficial (coordenadas exatas) e o alternativo
    (generate_fallback, layout genérico em reportlab)."""
    fixed = {
        'apr': 'APR - Modelo em branco.pdf',
        'pt_height': 'PT - Modelo em branco.pdf',
        'confined': 'PET Espaco Confinado - Modelo.pdf',
        'vehicle': 'Checklist Veiculo Pesado - Modelo.pdf',
    }
    if kind in fixed:
        return TEMPLATE_DIR / fixed[kind]
    if kind in {'electrical', 'line_live', 'vegetation', 'lifting', 'tme'}:
        name = MODULES.get(kind, {}).get('template')
        return TEMPLATE_DIR / name if name else None
    if kind in {'hoist', 'light_vehicle', 'height_kit', 'climber_assist', 'safety_belt'}:
        name = INSPECTION_MODULES.get(kind, {}).get('template')
        return TEMPLATE_DIR / name if name else None
    return None



def _rac_rect(values):
    return fitz.Rect(*[float(v) for v in values])


def _rac_sample_fill(page, rect):
    """Sample the source cell background so overlays keep the official alternating row color."""
    try:
        pix=page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        x=max(0,min(pix.width-1,int(rect.x0+3)))
        y=max(0,min(pix.height-1,int((rect.y0+rect.y1)/2)))
        rgb=pix.pixel(x,y)[:3]
        return tuple(c/255 for c in rgb)
    except Exception:
        return (1,1,1)


def _rac_write_cell(page, rect, text, fontsize=5.0, min_fontsize=3.5, align=0, bold=False):
    rect=fitz.Rect(rect)
    fill=_rac_sample_fill(page,rect)
    inner_clear=fitz.Rect(rect.x0+0.7,rect.y0+0.7,rect.x1-0.7,rect.y1-0.7)
    page.draw_rect(inner_clear,color=fill,fill=fill,width=0,overlay=True)
    if not str(text or '').strip():
        return
    inner=fitz.Rect(rect.x0+2.0,rect.y0+1.6,rect.x1-2.0,rect.y1-1.2)
    fontname='hebo' if bold else 'helv'
    fs=float(fontsize)
    while fs>=min_fontsize:
        rc=page.insert_textbox(inner,str(text),fontsize=fs,fontname=fontname,color=(0,0,0),align=align,lineheight=1.02,overlay=True)
        if rc>=0: return
        fs-=0.25
    page.insert_textbox(inner,str(text),fontsize=min_fontsize,fontname=fontname,color=(0,0,0),align=align,lineheight=1.0,overlay=True)


def _rac_header_value(page, label_variants, value, right_limit=None):
    if not value: return
    label=None
    for variant in label_variants:
        rects=page.search_for(variant)
        if rects:
            label=rects[0]; break
    if not label: return
    x1=right_limit if right_limit is not None else page.rect.width-30
    rect=fitz.Rect(label.x1+5,label.y0-1,x1,label.y1+2)
    # Header area is white in the official PDFs.
    page.draw_rect(rect,color=(1,1,1),fill=(1,1,1),width=0,overlay=True)
    _fit_textbox(page,fitz.Rect(rect.x0,rect.y0+0.5,rect.x1,rect.y1),str(value),fontsize=6,min_fontsize=4.2,align=0,bold=False)


def _rac_fill_page_one(page, data):
    def put(label, value, x1=None):
        if not value: return
        rects=page.search_for(label)
        if not rects: return
        r=rects[0]
        target=fitz.Rect(r.x1+7,r.y0-1,(x1 or page.rect.width-30),r.y1+2)
        page.draw_rect(target,color=(1,1,1),fill=(1,1,1),width=0,overlay=True)
        _fit_textbox(page,target,str(value),fontsize=6,min_fontsize=4.2,align=0)
    # Page 1 official identification block.
    put('FORNECEDOR AVALIADO',data.get('contractor',''),455)
    put('SITE / ATIVO',' / '.join(x for x in [data.get('cluster',''),data.get('site','')] if x),760)
    put('ESCOPO DOS SERVIÇOS',data.get('activity',''),455)
    put('AUDITOR RESPONSÁVEL',data.get('responsible_name',''),455)
    put('DATA DA AVALIAÇÃO',data.get('inspection_date',''),760)


def _rac_fill_repeated_header(page, data):
    supplier=page.search_for('Fornecedor:') or page.search_for('Fornece')
    date=page.search_for('Data:')
    auditor=page.search_for('Auditor:')
    if supplier and date:
        r=supplier[0]; d=date[0]
        target=fitz.Rect(r.x1+3,r.y0-1,d.x0-5,r.y1+2)
        page.add_redact_annot(target, fill=(1,1,1))
        page.apply_redactions(images=0, graphics=0)
        _fit_textbox(page,target,str(data.get('contractor','')),fontsize=5.2,min_fontsize=3.8)
    if date and auditor:
        d=date[0]; a=auditor[0]
        target=fitz.Rect(d.x1+3,d.y0-1,a.x0-5,d.y1+2)
        page.add_redact_annot(target, fill=(1,1,1))
        page.apply_redactions(images=0, graphics=0)
        _fit_textbox(page,target,str(data.get('inspection_date','')),fontsize=5.2,min_fontsize=3.8,align=1)
    if auditor:
        a=auditor[0]
        target=fitz.Rect(a.x1+3,a.y0-1,page.rect.width-28,a.y1+2)
        page.add_redact_annot(target, fill=(1,1,1))
        page.apply_redactions(images=0, graphics=0)
        _fit_textbox(page,target,str(data.get('responsible_name','')),fontsize=5.2,min_fontsize=3.8,align=1)


def _rac_add_action_annex(doc, cfg, flat_items, data):
    from .rac_reports import append_actions
    append_actions(doc, cfg, flat_items, data)


def _rac_add_photo_annex(doc, cfg, flat_items, data):
    from .rac_reports import append_photos
    append_photos(doc, cfg, flat_items, data, _sig_abs)


def generate_rac_original(kind: str, data: dict, out_pdf: Path):
    cfg=RAC_MODULES[kind]
    layout=RAC_PDF_LAYOUTS.get(kind)
    source=RAC_TEMPLATE_DIR / str(cfg.get('pdf_template') or cfg.get('source_file') or '')
    if not layout or not source.exists():
        return None
    doc=fitz.open(source)
    _rac_fill_page_one(doc[0],data)
    answers=list(data.get('answers') or [])
    observations=list(data.get('observations') or [])
    plans=list(data.get('action_plans') or [])
    label_map={'ATENDE':'Atende','NAO_ATENDE':'Não atende','NA':'N/A','SIM':'Sim','NAO':'Não'}
    touched_pages=set()
    for idx,row in enumerate(layout.get('items') or []):
        pno=int(row['page']); page=doc[pno]; touched_pages.add(pno)
        rects=row['rects']
        ans=answers[idx] if idx<len(answers) else ''
        obs=observations[idx] if idx<len(observations) else ''
        plan=plans[idx] if idx<len(plans) and isinstance(plans[idx],dict) else {}
        _rac_write_cell(page,_rac_rect(rects[4]),label_map.get(ans,ans),fontsize=4.8,min_fontsize=3.4,align=1,bold=(ans in {'NAO_ATENDE','NAO'}))
        _rac_write_cell(page,_rac_rect(rects[5]),obs,fontsize=4.4,min_fontsize=3.0)
        if ans in {'NAO_ATENDE','NAO'}:
            _rac_write_cell(page,_rac_rect(rects[6]),plan.get('action',''),fontsize=4.2,min_fontsize=2.8)
            _rac_write_cell(page,_rac_rect(rects[7]),plan.get('responsible',''),fontsize=4.2,min_fontsize=2.8)
            _rac_write_cell(page,_rac_rect(rects[8]),plan.get('due_date',''),fontsize=4.0,min_fontsize=2.8,align=1)
            status={'Pendente':'Não iniciado','Não iniciado':'Não iniciado'}.get(plan.get('status',''),plan.get('status','') or 'Não iniciado')
            _rac_write_cell(page,_rac_rect(rects[9]),status,fontsize=3.9,min_fontsize=2.6,align=1)
        else:
            for ci in range(6,10): _rac_write_cell(page,_rac_rect(rects[ci]),'',fontsize=4)
    for pno in touched_pages:
        _rac_fill_repeated_header(doc[pno],data)
    # Section adherence row: update score and nonconformity count without changing the official layout.
    offset=0
    for group in layout.get('groups') or []:
        count=int(group.get('item_count') or 0)
        a=answers[offset:offset+count]
        ok=sum(1 for x in a if x in {'ATENDE','SIM'})
        bad=sum(1 for x in a if x in {'NAO_ATENDE','NAO'})
        na=sum(1 for x in a if x=='NA')
        denom=ok+bad
        score=(ok/denom*100) if denom else None
        adh=group.get('adherence')
        if adh:
            page=doc[int(adh['page'])]; xs=adh['xs']; y0=float(adh['y0']); y1=float(adh['y1'])
            # Attendance, observations(meta), action(summary) are black in the official source row.
            for ci,text in [(4,(f'{score:.1f}%' if score is not None else 'N/A')),(5,'Meta: 95%'),(6,f'{bad} não atende(m) | {na} N/A')]:
                r=fitz.Rect(xs[ci]+1,y0+1,xs[ci+1]-1,y1-1)
                page.draw_rect(r,color=(0.07,0.07,0.07),fill=(0.07,0.07,0.07),width=0,overlay=True)
                page.insert_textbox(fitz.Rect(r.x0+2,r.y0+1,r.x1-2,r.y1-1),text,fontsize=5.2 if ci!=6 else 4.3,fontname='hebo' if ci==4 else 'helv',color=(1,1,1),align=1 if ci==4 else 0,lineheight=1.0,overlay=True)
        offset+=count
    # Remove o consolidado estático (fórmulas e datas de exemplo) e gera todos os valores.
    from .rac_reports import append_summary
    if doc.page_count and 'consolidado' in doc[-1].get_text().lower():
        doc.delete_page(doc.page_count - 1)
    append_summary(doc, cfg, data)
    flat_items=[]
    for g in cfg.get('groups',[]): flat_items.extend(g.get('items',[]))
    _rac_add_action_annex(doc,cfg,flat_items,data)
    _rac_add_photo_annex(doc,cfg,flat_items,data)
    out_pdf.parent.mkdir(parents=True,exist_ok=True)
    return _publish(doc,out_pdf)


def generate_rac(kind: str, data: dict, out_pdf: Path):
    """Finaliza a RAC no PDF oficial quando o modelo foi fornecido; mantém fallback para os demais."""
    if kind in RAC_PDF_LAYOUTS and RAC_MODULES[kind].get('pdf_template'):
        original=generate_rac_original(kind,data,out_pdf)
        if original is not None:
            return original
    import html
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    cfg=RAC_MODULES[kind]
    styles=_fallback_styles()
    out_pdf.parent.mkdir(parents=True,exist_ok=True)
    story=[]

    def esc(value):
        return html.escape(str(value or '')).replace('\n','<br/>')

    doc_title=str(cfg.get('title') or DOCUMENT_TITLES.get(kind,kind))
    doc_sub=f"Código: {data.get('code','')} · {cfg.get('revision') or 'Modelo original'}"
    story.append(Paragraph(esc(' '.join(doc_sub.split())),styles['sub']))

    general=[
        ['Cluster',data.get('cluster','')],['Site',data.get('site','')],
        ['Empresa / Contratada',data.get('contractor','')],['Data',data.get('inspection_date','')],
        ['Atividade / Objetivo',data.get('activity','')],['Responsável',data.get('responsible_name','')],
    ]
    gt=Table([[Paragraph(esc(a),styles['cell']),Paragraph(esc(b),styles['cell'])] for a,b in general],
             colWidths=[120,355])
    gt.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#E3DFD9')),
        ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#EDE9E5')),('LINEBEFORE',(0,0),(0,-1),2.5,colors.HexColor('#FF5246')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
    ]))
    story.append(gt)
    story.append(Spacer(1,7))

    answers=list(data.get('answers') or [])
    observations=list(data.get('observations') or [])
    action_plans=list(data.get('action_plans') or [])
    flat_index=0
    for group in cfg.get('groups',[]):
        story.append(Paragraph(esc(group.get('name','Requisitos')),styles['h2']))
        rows=[[Paragraph('#',styles['header_cell']),Paragraph('Requisito',styles['header_cell']),
               Paragraph('Resposta',styles['header_cell']),Paragraph('Observação / Evidência',styles['header_cell'])]]
        for item in group.get('items',[]):
            answer=answers[flat_index] if flat_index<len(answers) else ''
            obs=observations[flat_index] if flat_index<len(observations) else ''
            text=item.get('text','')
            extra=[]
            if item.get('section') and item.get('section')!=group.get('name'):
                extra.append(f"<b>{esc(item.get('section'))}</b>")
            extra.append(esc(text))
            if item.get('requirement'):
                extra.append(f"<b>Requisito:</b> {esc(item.get('requirement'))}")
            if item.get('recommendation'):
                extra.append(f"<b>Recomendação:</b> {esc(item.get('recommendation'))}")
            label={**{'ATENDE':'Atende','NAO_ATENDE':'Não atende','NA':'N/A','SIM':'Sim','NAO':'Não'},**{str(v):str(l) for v,l in (cfg.get('response_options') or [])}}.get(answer,answer or '—')
            plan=action_plans[flat_index] if flat_index<len(action_plans) and isinstance(action_plans[flat_index],dict) else {}
            obs_parts=[]
            if obs:
                obs_parts.append(esc(obs))
            if answer in {'NAO_ATENDE','NAO'}:
                action=plan.get('action','')
                responsible=plan.get('responsible','')
                due=plan.get('due_date','')
                if action or responsible or due:
                    obs_parts.append('<b>PLANO DE AÇÃO</b>')
                    if action: obs_parts.append(f"<b>Ação:</b> {esc(action)}")
                    if responsible: obs_parts.append(f"<b>Responsável:</b> {esc(responsible)}")
                    if due: obs_parts.append(f"<b>Prazo:</b> {esc(due)}")
            rows.append([
                Paragraph(esc(item.get('number','')),styles['cell']),
                Paragraph('<br/>'.join(extra),styles['cell']),
                Paragraph(esc(label),styles['cell']),
                Paragraph('<br/>'.join(obs_parts) if obs_parts else '—',styles['cell']),
            ])
            flat_index+=1
        t=Table(rows,colWidths=[30,270,70,105],repeatRows=1)
        t.setStyle(TableStyle([
            ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#D8D3CC')),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#181818')),
            ('LINEBELOW',(0,0),(-1,0),1.5,colors.HexColor('#FF5246')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F7F5F2')]),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        story.append(t)

    ok=sum(1 for a in answers if a in {'ATENDE','SIM'})
    bad=sum(1 for a in answers if a in {'NAO_ATENDE','NAO'})
    na=sum(1 for a in answers if a=='NA')
    summary=f"Resumo: {ok} atende/sim · {bad} não atende/não"
    if na: summary+=f" · {na} N/A"
    if data.get('score') is not None:
        summary+=f" · Score: {float(data.get('score')):.1f}%"
    story.append(Spacer(1,8))
    story.append(Paragraph(esc(summary),styles['small']))

    if data.get('general_observations'):
        story.append(Paragraph('Observações gerais',styles['h2']))
        story.append(Paragraph(esc(data.get('general_observations')),styles['cell']))

    sig=_sig_abs(data.get('signature_image'))
    if sig:
        story.append(Paragraph('Rubrica do responsável',styles['h2']))
        try:
            story.append(Image(str(sig),width=48*mm,height=18*mm))
        except Exception:
            story.append(Paragraph('Rubrica registrada no sistema.',styles['small']))

    doc=SimpleDocTemplate(str(out_pdf),pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=26*mm,bottomMargin=16*mm,
                          title=cfg.get('title') or DOCUMENT_TITLES.get(kind,kind),author='Safety Plus')
    def _serena_chrome(canvas,d):
        w,h=A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#181818')); canvas.rect(0,h-18*mm,w,18*mm,stroke=0,fill=1)
        canvas.setFillColor(colors.HexColor('#FF5246')); canvas.rect(0,h-18*mm-1.6*mm,w,1.6*mm,stroke=0,fill=1)
        logo=BASE_DIR/'static'/'icons'/'icon-192.png'
        x=15*mm
        if logo.exists():
            try: canvas.drawImage(str(logo),x,h-15.5*mm,width=13*mm,height=13*mm,mask='auto'); x+=16*mm
            except Exception: pass
        canvas.setFillColor(colors.white); canvas.setFont('Helvetica-Bold',11)
        canvas.drawString(x,h-9.5*mm,doc_title[:70])
        canvas.setFillColor(colors.HexColor('#FFB3AD')); canvas.setFont('Helvetica',7.5)
        canvas.drawString(x,h-13.5*mm,'Safety Plus · Serena Energia')
        canvas.setFillColor(colors.white); canvas.setFont('Helvetica-Bold',9)
        canvas.drawRightString(w-15*mm,h-9.5*mm,str(data.get('code','')))
        canvas.setFillColor(colors.HexColor('#FFB3AD')); canvas.setFont('Helvetica',7.5)
        canvas.drawRightString(w-15*mm,h-13.5*mm,' '.join(str(cfg.get('revision') or 'Modelo original').split())[:40])
        canvas.setStrokeColor(colors.HexColor('#E3DFD9')); canvas.setLineWidth(0.5); canvas.line(15*mm,11*mm,w-15*mm,11*mm)
        canvas.setFillColor(colors.HexColor('#858585')); canvas.setFont('Helvetica',7)
        canvas.drawString(15*mm,7.5*mm,'Documento gerado pelo Safety Plus')
        canvas.drawRightString(w-15*mm,7.5*mm,f'Página {d.page}')
        canvas.restoreState()
    doc.build(story,onFirstPage=_serena_chrome,onLaterPages=_serena_chrome)

    # Evidências fotográficas: cada ponto com foto recebe uma folha própria no fim do PDF.
    evidence_photos=list(data.get('evidence_photos') or [])
    if any(evidence_photos):
        flat_items=[]
        for group in cfg.get('groups',[]):
            flat_items.extend(group.get('items',[]))
        observations=list(data.get('observations') or [])
        pdf=fitz.open(out_pdf)
        for idx,item_photos in enumerate(evidence_photos):
            rows=item_photos if isinstance(item_photos,list) else ([item_photos] if item_photos else [])
            for photo_no,rel in enumerate(rows,1):
                photo=_sig_abs(rel)
                if not photo or idx>=len(flat_items):
                    continue
                item=flat_items[idx]
                page=pdf.new_page(width=595.28,height=841.89)
                page.draw_rect(fitz.Rect(0,0,595.28,841.89),color=(1,1,1),fill=(1,1,1),overlay=True)
                number=str(item.get('number','') or (idx+1))
                page.insert_text((42,55),'ANEXO — EVIDÊNCIA FOTOGRÁFICA',fontsize=15,fontname='hebo',color=(0.08,0.08,0.08))
                page.insert_text((42,79),f"{cfg.get('title','RAC')} · Item {number}",fontsize=9.5,fontname='hebo',color=(0.75,0.20,0.16))
                question=' '.join(str(item.get('text','') or '').split())
                y_end=page.insert_textbox(fitz.Rect(42,96,553,155),f"Ponto verificado: {question}",fontsize=9,fontname='helv',color=(0.12,0.12,0.12),lineheight=1.15)
                obs=observations[idx] if idx<len(observations) else ''
                top=165
                if obs:
                    page.insert_text((42,top),'Observação / evidência:',fontsize=8.5,fontname='hebo',color=(0.12,0.12,0.12))
                    page.insert_textbox(fitz.Rect(42,top+10,553,top+58),str(obs),fontsize=8,fontname='helv',color=(0.15,0.15,0.15),lineheight=1.15)
                    top+=70
                box=fitz.Rect(42,top,553,790)
                try:
                    pix=fitz.Pixmap(str(photo))
                    ratio=min(box.width/max(pix.width,1),box.height/max(pix.height,1))
                    w=pix.width*ratio; h=pix.height*ratio
                    rect=fitz.Rect(box.x0+(box.width-w)/2,box.y0,box.x0+(box.width+w)/2,box.y0+h)
                    page.insert_image(rect,filename=str(photo),keep_proportion=True,overlay=True)
                    page.draw_rect(rect,color=(0.84,0.82,0.79),width=.6,overlay=True)
                except Exception:
                    page.insert_textbox(box,'Foto de evidência registrada, mas não foi possível renderizá-la neste PDF.',fontsize=9,fontname='helv',align=1)
        tmp=out_pdf.with_name(out_pdf.stem+'_evidence_tmp.pdf')
        pdf.save(tmp,garbage=4,deflate=True)
        pdf.close()
        os.replace(tmp,out_pdf)

    check=fitz.open(out_pdf)
    pages=check.page_count
    check.close()
    if pages<1:
        raise RuntimeError('PDF RAC inválido.')
    return out_pdf



def generate_safety_moment(data: dict, out_pdf: Path):
    """PDF do Momento de Segurança: identificação, tema, pontos abordados e lista de presença com rubricas."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from xml.sax.saxutils import escape
    st=_fallback_styles(); red=colors.HexColor('#D52D32')
    def P(v,style='cell'): return Paragraph(escape(str(v or '—')).replace('\n','<br/>'),st[style])
    def sig_img(value,w=70,h=26):
        pth=_sig_abs(value)
        if not pth: return P('—')
        try: return Image(str(pth),width=w,height=h,kind='proportional')
        except Exception: return P('—')
    story=[]
    left=ParagraphStyle('ms_l',parent=st['small'],fontSize=8,leading=11,textColor=colors.HexColor('#434343'))
    mark=ParagraphStyle('ms_m',parent=st['h1'],fontSize=22,leading=25,alignment=2,spaceAfter=0)
    head=Table([[Paragraph('<b>GESTÃO DE ATIVOS · SAÚDE E SEGURANÇA DO TRABALHO</b>',left),Paragraph('<font color="#D52D32"><b>SERENA</b></font>',mark)]],colWidths=[315,165])
    head.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),1.5,red),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story+=[head,Spacer(1,10),Paragraph('Momento de Segurança',st['h1']),Paragraph(f"Código: {escape(str(data.get('code','')))}",st['sub'])]
    info=[[P('Data'),P(data.get('moment_date')),P('Horário'),P(data.get('moment_time'))],
          [P('Cluster'),P(data.get('cluster')),P('Site'),P(data.get('site'))],
          [P('Tema'),P(data.get('theme')),P('Conduzido por'),P(data.get('conductor'))]]
    t=Table(info,colWidths=[60,175,70,175]); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.HexColor('#CFCBC6')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F4F1EC')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#F4F1EC')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story+=[t,Paragraph('Pontos abordados',st['h2']),P(data.get('key_points')),Paragraph('Lista de presença',st['h2'])]
    rows=[[Paragraph('Nº',st['header_cell']),Paragraph('Nome',st['header_cell']),Paragraph('Empresa',st['header_cell']),Paragraph('Função',st['header_cell']),Paragraph('Rubrica',st['header_cell'])]]
    for i,pp in enumerate(data.get('participants') or [],1):
        rows.append([P(i),P(pp.get('name')),P(pp.get('company')),P(pp.get('role')),sig_img(pp.get('signature_image'))])
    if len(rows)==1: rows.append([P('—')]*5)
    tb=Table(rows,colWidths=[24,150,110,100,96],repeatRows=1)
    tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),red),('GRID',(0,0),(-1,-1),.5,colors.HexColor('#CFCBC6')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story+=[tb,Spacer(1,16)]
    cs=Table([[P('Responsável pelo momento'),sig_img(data.get('conductor_signature'),150,40)],[P(data.get('conductor')),P('Assinatura')]],colWidths=[200,260])
    cs.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.5,colors.HexColor('#CFCBC6')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F4F1EC'))]))
    story.append(cs)
    out_pdf.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(out_pdf),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=16*mm,bottomMargin=16*mm,title='Momento de Segurança').build(story)

# =====================================================================
# MODELO PADRÃO DE CHECKLIST — PDF no layout Serena (daily e single)
# =====================================================================
_STD_RED = '#D52D32'


def _std_header_table(title, ref, width):
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    brand = Paragraph(f'<font color="{_STD_RED}" size="20"><b>serena</b></font>', ParagraphStyle('b', fontName='Helvetica'))
    ttl = Paragraph(f'<b>{title.upper()}</b>', ParagraphStyle('t', fontName='Helvetica', fontSize=10, alignment=1))
    rf = Paragraph(ref, ParagraphStyle('r', fontName='Helvetica', fontSize=6.5, alignment=1, leading=8))
    t = Table([[brand, ttl, rf]], colWidths=[width * .2, width * .6, width * .2], rowHeights=[34])
    t.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 1, colors.black), ('INNERGRID', (0, 0), (-1, -1), .6, colors.black),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, 0), 'CENTER')]))
    return t


def _std_prepare_image(path, max_side, flatten_white):
    """Normaliza imagens para o PDF: corrige rotação EXIF, achata transparência sobre fundo
    branco (evita quadro preto no celular), reduz tamanho e converte para JPEG leve."""
    import io
    from PIL import Image as PILImage, ImageOps
    with PILImage.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ('RGBA', 'LA', 'P'):
            im = im.convert('RGBA')
            bg = PILImage.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert('RGB')
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=88 if not flatten_white else 92, optimize=True)
        buf.seek(0)
        return buf


def _std_sig(value, w=58, h=16, stamp=True, fs=6):
    """Rubrica em destaque (tinta escura) com data e hora da assinatura logo abaixo."""
    from reportlab.platypus import Image, Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    p = _sig_abs(value)
    if not p:
        return ''
    try:
        data = _sig_enhanced(p)
        img = Image(io.BytesIO(data) if data else _std_prepare_image(p, 900, True), width=w, height=h, kind='proportional')
    except Exception:
        return ''
    txt = _sig_stamp(value)
    if not (stamp and txt):
        return img
    cap = Paragraph(f'<b>Assinado em {txt}</b>', ParagraphStyle('sg', fontName='Helvetica', fontSize=fs, leading=fs + 1.5, alignment=1))
    t = Table([[img], [cap]], colWidths=[w], rowHeights=[h, fs + 3])
    t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    return t


def _std_photo_entries(kind, cfg, data):
    """Lista (legenda, caminho) de todas as fotos anexadas, indicando de onde vêm."""
    out = []
    def flat(v):
        for x in (v or []):
            if isinstance(x, list):
                yield from flat(x)
            elif x:
                yield x
    if cfg['mode'] == 'daily':
        for per in cfg['periods']:
            info = (data.get('periods') or {}).get(per) or {}
            ph = info.get('photos') or []
            for i, it in enumerate(cfg['items']):
                sub = ph[i] if i < len(ph) else []
                for rel in flat(sub if isinstance(sub, list) else [sub]):
                    out.append((f"{per} - Item {i+1}: {it[0]}", rel))
    else:
        for i, r in enumerate(data.get('rows') or []):
            it = cfg['items'][i] if i < len(cfg['items']) else ('',)
            num = it[1] if len(it) > 1 else str(i + 1)
            for rel in flat((r or {}).get('photos')):
                out.append((f"Item {num}: {it[0]}", rel))
    return out


def _std_photo_flowables(entries, W):
    from reportlab.platypus import Paragraph, Image, PageBreak, KeepTogether, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    res = []
    cap = ParagraphStyle('pc', fontName='Helvetica-Bold', fontSize=9, leading=11)
    for n, (legenda, rel) in enumerate(entries, 1):
        path = _sig_abs(rel)
        if not path:
            continue
        try:
            img = Image(_std_prepare_image(path, 2000, False), width=W, height=120 * mm, kind='proportional')
        except Exception:
            continue
        res.append(KeepTogether([Paragraph(f'Foto {n} — {legenda}', cap), Spacer(1, 3), img, Spacer(1, 10)]))
    if res:
        res.insert(0, PageBreak())
        res.insert(1, Paragraph('<b>REGISTRO FOTOGRÁFICO</b>', ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=11)))
        res.insert(2, Spacer(1, 8))
    return res


def generate_standard_checklist(kind: str, data: dict, out_pdf: Path, cfg_override: dict | None = None):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    cfg = cfg_override or INSPECTION_MODULES[kind]
    title = cfg['short'].replace('Lista de Verificação — ', 'Lista de Verificação - ')
    daily = cfg['mode'] == 'daily'
    page = landscape(A4) if daily else A4
    margin = 10 * mm
    W = page[0] - 2 * margin
    cell = ParagraphStyle('c', fontName='Helvetica', fontSize=7.2, leading=8.6)
    small = ParagraphStyle('s', fontName='Helvetica-Oblique', fontSize=6.5, leading=8)
    story = [_std_header_table(title, (cfg.get('ref') or ('Ref.: RAC - Norma<br/>regulamentadora/Içamento de Cargas' if kind == 'lifting_accessories' else 'Ref. Norma<br/>regulamentadora/Fabricante')), W)]

    # campos do cabeçalho (igual ao modelo oficial)
    lab = ParagraphStyle('lab', fontName='Helvetica-Bold', fontSize=7.2, leading=9)
    def fld(label, val):
        return Paragraph(f'<b>{label.upper()}:</b> {val}', lab)
    gv = lambda k: str(data.get(k) or '')
    if daily:
        fl = dict(cfg['fields'])
        model_lbl = fl.get('model', 'Modelo').upper().replace(' DA ', ' ').replace(' DO ', ' ')
        r1 = [fld('Cluster', gv('cluster')), fld('Local', gv('local')), fld(model_lbl, gv('model')),
              fld('Mês', gv('month') or '_____'), fld('Ano', gv('year') or '20_____')]
        info = Table([r1, [fld('Líder', gv('leader')), '', '', '', '']],
                     colWidths=[W * .2, W * .3, W * .27, W * .11, W * .12])
        info.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .8, colors.black), ('INNERGRID', (0, 0), (-1, 0), .4, colors.black),
                                  ('SPAN', (0, 1), (-1, 1)), ('LINEABOVE', (0, 1), (-1, 1), .4, colors.black),
                                  ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    else:
        flds = [(l, gv(k)) for k, l in cfg['fields']] + ([('Dia', gv('weekday'))] if gv('weekday') else []) + ([('Mês/Ano', f"{gv('month')}/{gv('year')}")] if gv('month') else []) + [('Data da inspeção', gv('inspection_date'))]
        rows = [[fld(l, v)] for l, v in flds]
        info = Table(rows, colWidths=[W])
        info.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .8, colors.black), ('INNERGRID', (0, 0), (-1, -1), .4, colors.black),
                                  ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    story.append(info)
    if kind == 'light_vehicle':
        details = Table([[fld(label, gv(key)) for key, label in cfg['fields']]],
                        colWidths=[W / len(cfg['fields'])] * len(cfg['fields']))
        details.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .4, colors.black),
                                    ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(details)
        if data.get('nonconformities'):
            rows = [[Paragraph('<b>Item</b>', cell), Paragraph('<b>Ação</b>', cell),
                     Paragraph('<b>Responsável</b>', cell), Paragraph('<b>Data</b>', cell)]]
            for row in data['nonconformities']:
                rows.append([Paragraph(str(row.get(key) or ''), cell)
                             for key in ('item', 'action', 'responsible', 'date')])
            actions = Table(rows, colWidths=[W*.1, W*.55, W*.2, W*.15], repeatRows=1)
            actions.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .4, colors.black),
                                        ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
            story += [Spacer(1, 6), actions]

    items = cfg['items']
    hdr_bg = colors.HexColor('#4D4D4D')
    if daily:
        periods = cfg['periods']; pdata = data.get('periods') or {}
        num_w = 7 * mm; day_w = 3 * 9.2 * mm
        txt_w = W - num_w - day_w * 0 - 7 * 3 * 9.2 * mm
        cw = [num_w, max(txt_w, 60 * mm)] + [9.2 * mm] * 21
        head1 = ['', ''] + sum(([(p + '-feira') if p not in ('Sábado', 'Domingo') else p, '', ''] for p in periods), [])
        head2 = ['', 'ITENS PARA VERIFICAR'] + ['C', 'NC', 'NA'] * 7
        head3 = ['', ''] + sum(([ (pdata.get(p) or {}).get('date') or '__/__', '', ''] for p in periods), [])
        body = []
        for i, it in enumerate(items):
            row = [str(i + 1), Paragraph(it[0], cell)]
            for p in periods:
                ans = ((pdata.get(p) or {}).get('answers') or [])
                a = ans[i] if i < len(ans) else ''
                row += ['X' if a == v else '' for v in ('C', 'NC', 'NA')]
            body.append(row)
        sig = ['', Paragraph('Visto (rubrica) — a inspeção deve ser realizada diariamente.', small)]
        for p in periods:
            sg = _std_sig((pdata.get(p) or {}).get('signature_image'), 62, 24, True, 4.2)
            sig += [sg, '', '']
        data_rows = [head1, head3, head2] + body + [sig]
        t = Table(data_rows, colWidths=cw, repeatRows=3)
        st = [('GRID', (0, 0), (-1, -1), .4, colors.black), ('FONTSIZE', (0, 0), (-1, -1), 7), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
              ('ALIGN', (2, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
              ('BACKGROUND', (0, 2), (-1, 2), hdr_bg), ('TEXTCOLOR', (0, 2), (-1, 2), colors.white),
              ('FONTNAME', (2, 0), (-1, 0), 'Helvetica-Bold')]
        for d in range(7):
            c0 = 2 + d * 3
            st += [('SPAN', (c0, 0), (c0 + 2, 0)), ('SPAN', (c0, 1), (c0 + 2, 1)), ('SPAN', (c0, len(data_rows) - 1), (c0 + 2, len(data_rows) - 1))]
        t.setStyle(TableStyle(st))
        story += [t, Spacer(1, 4), Paragraph('Estou ciente que todos os itens acima verificados são de minha responsabilidade, e que devo executar a atividade com segurança.', small)]
    else:
        rows_data = data.get('rows') or []
        scale = cfg.get('scale')
        sc_vals = [x[0] for x in scale] if scale else ['ATENDE', 'NAO_ATENDE', 'NA']
        head = ['', 'ITENS PARA INSPECIONAR'] + ([x[1] for x in scale] if scale else ['C', 'NC', 'N.A.']) + ['OBSERVAÇÕES']
        body = []; sec_rows = []; any_nc = False; last = None
        for i, it in enumerate(items):
            r = rows_data[i] if i < len(rows_data) else {}
            a = r.get('answer')
            any_nc = any_nc or a == 'NAO_ATENDE'
            sec, _, txt = it[0].partition(': ') if cfg.get('grouped') else ('', '', it[0])
            if not txt:
                sec, txt = '', it[0]
            if sec != last and sec:
                sec_rows.append(len(body)); body.append([sec.upper(), '', '', '', '', '']); body.append(head)
                last = sec
            obs = ' '.join(x for x in (r.get('evidence'), r.get('action')) if x)
            num = (it[1].split('.')[-1] if (cfg.get('grouped') and len(it) > 1) else str(i + 1))
            body.append([num, Paragraph(txt, cell)] + ['X' if a == v else '' for v in sc_vals] + [Paragraph(obs, cell)])
        if not cfg.get('grouped'):
            body.insert(0, head)
        t = Table(body, colWidths=[8 * mm, W - 8 * mm - 3 * 9 * mm - 55 * mm, 9 * mm, 9 * mm, 9 * mm, 55 * mm])
        st = [('GRID', (0, 0), (-1, -1), .4, colors.black), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
              ('FONTSIZE', (0, 0), (-1, -1), 7), ('ALIGN', (2, 0), (4, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
        if not cfg.get('grouped'):
            st += [('BACKGROUND', (0, 0), (-1, 0), hdr_bg), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)]
        for r_i in sec_rows:
            st += [('SPAN', (0, r_i), (-1, r_i)), ('BACKGROUND', (0, r_i), (-1, r_i), colors.HexColor('#E6E2DC')),
                   ('ALIGN', (0, r_i), (-1, r_i), 'CENTER'), ('BACKGROUND', (0, r_i + 1), (-1, r_i + 1), hdr_bg),
                   ('TEXTCOLOR', (0, r_i + 1), (-1, r_i + 1), colors.white)]
        t.setStyle(TableStyle(st))
        story += [t, Spacer(1, 6)]
        if cfg.get('note'):
            story.append(Paragraph(cfg['note'], small))
        res = ('REPROVADO' if any_nc else 'APROVADO') if cfg.get('scale') else ('INAPTO AO TRABALHO' if any_nc else 'APTO AO TRABALHO')
        story += [Spacer(1, 6), Paragraph(f'<b>RESULTADO DA INSPEÇÃO: {res}</b>', ParagraphStyle('rs', fontName='Helvetica', fontSize=9)),
                  Spacer(1, 4), Paragraph('Declaro que todas as informações repassadas para esta Lista de Verificação durante a inspeção são verdadeiras.', small),
                  Spacer(1, 4)]
        _sg = _std_sig(data.get('signature_image'), 190, 62, True, 8)
        if _sg != '':
            story.append(_sg)

    obs_txt = (data.get('observations') or '').strip()
    story += [Spacer(1, 6), Paragraph('<b>Observações/Indicações de não conformidades:</b> ' + obs_txt, cell), Spacer(1, 4),
              Paragraph('Condição: A - Aprovado · AR - Aprovado com restrição · R - Reprovado' if cfg.get('scale') else 'Condição: C - Conforme · NC - Não Conforme · NA - Não Aplicável · * - Item impeditivo', small),
              Paragraph(f"Código: {data.get('code', '')}", small)]
    story += _std_photo_flowables(_std_photo_entries(kind, cfg, data), W)
    doc = SimpleDocTemplate(str(out_pdf), pagesize=page, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin, title=title)
    doc.build(story)
    return out_pdf


_DAY_MAP = {'C': 'ATENDE', 'NC': 'NAO_ATENDE', 'NA': 'NA'}


def generate_day_checklist(kind: str, data: dict, out_pdf: Path, cfg: dict | None = None):
    """Folha própria de UM dia: itens com C/NC/NA, data, rubrica e fotos (sem a grade semanal)."""
    cfg = cfg or INSPECTION_MODULES[kind]
    per = data.get('day_period') or ''
    info = (data.get('periods') or {}).get(per) or {}
    photos = info.get('photos') or []
    rows = []
    for i, _it in enumerate(cfg['items']):
        ans = (info.get('answers') or [])
        a = ans[i] if i < len(ans) else ''
        rows.append({'answer': _DAY_MAP.get(a, ''), 'evidence': '', 'action': '', 'photos': photos[i] if i < len(photos) and isinstance(photos[i], list) else []})
    d2 = dict(data)
    wd = {'Segunda': 'Segunda-feira', 'Terça': 'Terça-feira', 'Quarta': 'Quarta-feira', 'Quinta': 'Quinta-feira', 'Sexta': 'Sexta-feira'}.get(per, per)
    d2.update({'rows': rows, 'inspection_date': info.get('date', ''), 'signature_image': info.get('signature_image', ''), 'weekday': wd})
    cfg2 = dict(cfg); cfg2['mode'] = 'single'; cfg2['layout'] = 'standard'; cfg2['note'] = cfg.get('note') or 'Caso algum item esteja não conforme, o equipamento está inapto para o trabalho. Itens marcados com * são impeditivos.'
    return generate_standard_checklist(kind, d2, out_pdf, cfg2)


def generate_vehicle_day(data: dict, out_pdf: Path):
    """Veículo pesado em modo dia: mesma folha padrão das demais inspeções, só o dia em questão."""
    from .module_configs import VEHICLE_CHECK_ITEMS
    per = data.get('day_period') or ''
    info = (data.get('days') or {}).get(per) or {}
    done = str(info.get('completed_at') or '')[:10]
    try:
        date_br = f'{done[8:10]}/{done[5:7]}/{done[0:4]}' if len(done) == 10 else ''
    except Exception:
        date_br = ''
    pdata = {per: {'answers': info.get('answers') or [], 'photos': info.get('photos') or [],
                   'date': date_br, 'signature_image': info.get('signature_image') or ''}}
    cfg = {'short': 'Inspeção de Veículo Pesado', 'mode': 'daily', 'layout': 'standard', 'periods': [per],
           'items': [(t,) for t in VEHICLE_CHECK_ITEMS],
           'fields': [('cluster', 'Cluster'), ('site', 'Local'), ('model', 'Veículo'), ('operator', 'Operador')]}
    d2 = dict(data); d2['periods'] = pdata
    d2['local'] = data.get('site', ''); d2['leader'] = data.get('operator', '')
    return generate_day_checklist('vehicle', dict(d2, day_mode=True, day_period=per), out_pdf, cfg)


def generate_document(kind: str, data: dict, out_pdf: Path):
    if kind=='safety_moment': return generate_safety_moment(data,out_pdf)
    if kind=='vehicle' and isinstance(data,dict) and data.get('day_mode'): return generate_vehicle_day(data,out_pdf)
    if kind in INSPECTION_MODULES and isinstance(data,dict) and data.get('day_mode'): return generate_day_checklist(kind,data,out_pdf)
    template = _expected_template_path(kind)
    if template is not None and (not template.exists() or template.stat().st_size < 1024):
        # O arquivo-modelo oficial da Serena ainda não foi fornecido para
        # este tipo de documento. Em vez de travar o fluxo (finalizar a
        # PT/inspeção/APR), gera um PDF alternativo simples com os mesmos
        # dados, deixando claro que não é o layout oficial. Assim que o
        # arquivo real for colocado em app/pdf_templates/ com o nome
        # esperado, esta função volta a usar o gerador com coordenadas
        # exatas automaticamente — nada mais precisa mudar.
        return generate_fallback(kind, data, out_pdf)
    if kind=='apr': return generate_apr(data,out_pdf)
    if kind=='vehicle': return generate_vehicle(data,out_pdf)
    if kind=='hoist': return generate_hoist(data,out_pdf)
    if kind=='light_vehicle': return generate_light_vehicle(data,out_pdf)
    if kind=='height_kit': return generate_height_kit(data,out_pdf)
    if kind=='climber_assist': return generate_climber_assist(data,out_pdf)
    if kind=='safety_belt': return generate_fallback(kind,data,out_pdf)
    if kind in INSPECTION_MODULES and INSPECTION_MODULES[kind].get('layout')=='standard': return generate_standard_checklist(kind,data,out_pdf)
    if kind in INSPECTION_MODULES: return generate_fallback(kind,data,out_pdf)
    if kind=='pt_height': return generate_pt_height(data,out_pdf)
    if kind=='confined': return generate_confined(data,out_pdf)
    if kind in {'electrical','line_live'}: return generate_electrical_like(kind,data,out_pdf)
    if kind in {'vegetation','lifting','tme'}:
        # Algumas instalações receberam o PDF-modelo antes de as coordenadas
        # oficiais desses formulários existirem no config. Nessa situação,
        # usar generate_standard causava KeyError (ex.: 'activity_rect') no celular.
        # O PDF alternativo preserva os dados e evita o erro até o layout oficial
        # estar completamente configurado.
        cfg=MODULES.get(kind,{})
        required={'activity_rect','check_ys'}
        if not required.issubset(cfg):
            return generate_fallback(kind,data,out_pdf)
        return generate_standard(kind,data,out_pdf)
    if kind in RAC_MODULES: return generate_rac(kind,data,out_pdf)
    raise ValueError(f'Tipo de documento não suportado: {kind}')
