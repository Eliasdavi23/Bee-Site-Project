"""
Serviço de geração de documentos em PDF de alta resolução (A4).

100% Localhost, sem dependências de CDN ou serviços externos.
Utiliza ReportLab para renderização rápida e tipografia técnica limpa.
"""
import io
import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_INSTALADO = True
except ImportError:
    REPORTLAB_INSTALADO = False
    A4 = None
    colors = None
    canvas = None
    SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = KeepTogether = HRFlowable = None  # type: ignore[assignment,misc]
    getSampleStyleSheet = ParagraphStyle = None  # type: ignore[assignment]

DIR_UPLOADS_PDF = os.path.join("static", "uploads", "orcamentos")


def formatar_moeda(valor) -> str:
    v = float(valor or 0.0)
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


if REPORTLAB_INSTALADO and canvas is not None:
    class PaginacaoCanvas(canvas.Canvas):
        """Canvas com duas passagens para calcular o total exato de páginas."""
        nome_empresa = "BEE GRÁFICA DIGITAL"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_paginas = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._desenhar_rodape(num_paginas)
                super().showPage()
            super().save()

        def _desenhar_rodape(self, total_paginas: int):
            self.saveState()
            self.setStrokeColor(colors.HexColor("#E4E4E7"))
            self.setLineWidth(0.8)
            self.line(36, 40, 559, 40)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#71717A"))
            emp_rodape = getattr(self, "nome_empresa", None) or "BEE GRÁFICA & COMUNICAÇÃO VISUAL"
            self.drawString(36, 27, f"{emp_rodape} • Soluções em Impressão Digital")
            self.drawRightString(559, 27, f"Página {self._pageNumber} de {total_paginas}")
            self.restoreState()
else:
    class PaginacaoCanvas:  # type: ignore[no-redef]
        nome_empresa = "BEE GRÁFICA DIGITAL"


def obter_dados_empresa_db() -> dict:
    """Busca as configurações institucionais da empresa no banco de dados."""
    try:
        from config.database import get_connection
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT chave, valor FROM configuracoes")
            return {row["chave"]: (row["valor"] or "").strip() for row in cursor.fetchall()}
        finally:
            conn.close()
    except Exception as e:
        print(f"Erro ao obter configuracoes da empresa para PDF: {e}")
        return {}


def formatar_linha_contato_empresa(empresa: dict) -> str:
    """Formata a linha 'Cidade / UF • Telefone/WhatsApp: (XX) XXXXX-XXXX'."""
    cidade = (empresa.get("cidade_empresa") or "").strip()
    estado = (empresa.get("estado_empresa") or "").strip().upper()
    telefone = (empresa.get("telefone_empresa") or "").strip()

    loc = ""
    if cidade and estado:
        loc = f"{cidade} / {estado}"
    elif cidade:
        loc = cidade
    elif estado:
        loc = estado

    tel = f"Telefone/WhatsApp: {telefone}" if telefone else ""

    partes = [p for p in (loc, tel) if p]
    return " • ".join(partes)


def gerar_pdf_orcamento(orcamento: dict, empresa: dict | None = None) -> bytes:
    """
    Gera o PDF oficial do Orçamento / Proposta Comercial em formato A4.
    Retorna os bytes do arquivo em memória.
    """
    if not REPORTLAB_INSTALADO or SimpleDocTemplate is None:
        raise RuntimeError(
            "O módulo 'reportlab' não está instalado no ambiente Python. "
            "Execute no terminal: pip install reportlab"
        )

    if empresa is None:
        empresa = orcamento.get("empresa") or obter_dados_empresa_db()

    empresa_nome = (empresa.get("nome_empresa") or "").strip() or "BEE GRÁFICA & COMUNICAÇÃO"
    empresa_subtitulo = (empresa.get("subtitulo_empresa") or "").strip() or "Gestão de Produção Gráfica e Impressão Digital"
    linha_contato = formatar_linha_contato_empresa(empresa)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    style_empresa_titulo = ParagraphStyle(
        "EmpresaTitulo",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#18181B"),
    )
    style_doc_titulo = ParagraphStyle(
        "DocTitulo",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=2,
        textColor=colors.HexColor("#CA8A04"),
    )
    style_secao_tit = ParagraphStyle(
        "SecaoTitulo",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#18181B"),
        textTransform="uppercase",
    )
    style_texto = ParagraphStyle(
        "TextoPadrao",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#27272A"),
    )
    style_texto_bold = ParagraphStyle(
        "TextoBold",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#18181B"),
    )
    style_item_desc = ParagraphStyle(
        "ItemDesc",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#18181B"),
    )
    style_item_obs = ParagraphStyle(
        "ItemObs",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#71717A"),
    )
    style_tabela_header = ParagraphStyle(
        "TabelaHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )
    style_tabela_cell_centro = ParagraphStyle(
        "CellCentro",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor("#27272A"),
    )
    style_tabela_cell_dir = ParagraphStyle(
        "CellDir",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.HexColor("#27272A"),
    )

    story = []

    # 1. CABEÇALHO
    info_contato_html = f"<br/>{linha_contato}" if linha_contato else ""
    header_data = [
        [
            Paragraph(
                f"<b>{empresa_nome}</b><br/>"
                f"<font color='#71717A' size='8'>{empresa_subtitulo}{info_contato_html}</font>",
                style_empresa_titulo,
            ),
            Paragraph(
                f"<b>PROPOSTA COMERCIAL</b><br/>"
                f"<font color='#18181B' size='11'><b>Orçamento #{orcamento.get('id', '-')}</b></font><br/>"
                f"<font color='#71717A' size='8'>Data: {orcamento.get('data', datetime.now().strftime('%d/%m/%Y'))}<br/>"
                f"Atendente: {orcamento.get('usuario_nome', 'Comercial')}</font>",
                style_doc_titulo,
            ),
        ]
    ]
    t_header = Table(header_data, colWidths=[320, 203])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_header)

    # Linha divisória com destaque amarelo
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#EAB308"), spaceBefore=2, spaceAfter=10))

    # 2. DADOS DO CLIENTE E CONDIÇÕES
    cli_nome = orcamento.get("cliente_nome") or "Cliente Balcão"
    cli_doc = orcamento.get("cliente_documento") or "Não informado"
    cli_tel = orcamento.get("cliente_telefone") or "Não informado"
    cli_email = orcamento.get("cliente_email") or "Não informado"
    cli_end = orcamento.get("cliente_endereco") or "Não informado"

    dados_cli = [
        [
            Paragraph("<b>DADOS DO CLIENTE</b>", style_secao_tit),
            Paragraph("<b>CONDIÇÕES COMERCIAIS</b>", style_secao_tit),
        ],
        [
            Paragraph(
                f"<b>Cliente / Razão:</b> {cli_nome}<br/>"
                f"<b>CPF / CNPJ:</b> {cli_doc}<br/>"
                f"<b>Telefone / WhatsApp:</b> {cli_tel}<br/>"
                f"<b>E-mail:</b> {cli_email}<br/>"
                f"<b>Endereço:</b> {cli_end}",
                style_texto,
            ),
            Paragraph(
                "<b>Validade da Proposta:</b> 7 dias corridos<br/>"
                "<b>Início da Produção:</b> Mediante entrada de 50%<br/>"
                "<b>Forma de Pagamento:</b> Pix / Cartão / Transferência<br/>"
                "<b>Status do Orçamento:</b> Aberto para aprovação",
                style_texto,
            ),
        ]
    ]
    t_cli = Table(dados_cli, colWidths=[280, 243])
    t_cli.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_cli)
    story.append(Spacer(1, 14))

    # 3. TABELA DE ITENS DO ORÇAMENTO
    story.append(Paragraph("<b>RELAÇÃO DE PRODUTOS E ESPECIFICAÇÕES</b>", style_secao_tit))
    story.append(Spacer(1, 4))

    itens_tabela = [
        [
            Paragraph("<b>Item</b>", style_tabela_header),
            Paragraph("<b>Descrição do Produto & Acabamento</b>", ParagraphStyle("THL", parent=style_tabela_header, alignment=0)),
            Paragraph("<b>Qtd</b>", style_tabela_header),
            Paragraph("<b>Valor Unit.</b>", ParagraphStyle("THR", parent=style_tabela_header, alignment=2)),
            Paragraph("<b>Subtotal</b>", ParagraphStyle("THR2", parent=style_tabela_header, alignment=2)),
        ]
    ]

    itens = orcamento.get("itens") or []
    subtotal_calculado = 0.0

    for idx, it in enumerate(itens, 1):
        qtd = float(it.get("quantidade") or 1.0)
        qtd_fmt = f"{int(qtd)}" if qtd.is_integer() else f"{qtd:g}"
        preco_u = float(it.get("preco_unitario") or 0.0)
        sub = round(qtd * preco_u, 2)
        subtotal_calculado += sub
        obs_item = (it.get("observacao") or "").strip()

        desc_p = [Paragraph(f"<b>{it.get('nome_produto', 'Produto')}</b>", style_item_desc)]
        if obs_item:
            desc_p.append(Paragraph(f"Especificações / Acabamento: {obs_item}", style_item_obs))

        itens_tabela.append([
            Paragraph(str(idx), style_tabela_cell_centro),
            desc_p,
            Paragraph(qtd_fmt, style_tabela_cell_centro),
            Paragraph(formatar_moeda(preco_u), style_tabela_cell_dir),
            Paragraph(formatar_moeda(sub), style_tabela_cell_dir),
        ])

    t_itens = Table(itens_tabela, colWidths=[30, 273, 50, 85, 85])
    t_itens.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#18181B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    story.append(t_itens)
    story.append(Spacer(1, 10))

    # 4. TOTAIS E OBSERVAÇÕES
    desconto_val = float(orcamento.get("desconto") or 0.0)
    total_liquido = max(0.0, subtotal_calculado - desconto_val)
    obs_geral = (orcamento.get("observacao") or "").strip() or "Nenhuma observação adicional informada."

    totais_data = [
        [
            Paragraph("<b>OBSERVAÇÕES E NOTAS IMPORTANTES:</b>", style_texto_bold),
            Paragraph("Subtotal dos Itens:", style_texto),
            Paragraph(formatar_moeda(subtotal_calculado), style_texto_bold),
        ],
        [
            Paragraph(
                f"<font color='#52525B'>{obs_geral}</font><br/><br/>"
                "<font size='7' color='#71717A'>• Arquivos devem ser enviados em PDF/X-1a ou CMYK 300 DPI.<br/>"
                "• A produção será agendada após aprovação formal da prévia e confirmação do pagamento de entrada.<br/>"
                "• Materiais sujeitos a variação técnica de até 5% no corte/cor inerente ao processo gráfico.</font>",
                style_texto,
            ),
            Paragraph("Desconto Concedido:<br/><br/><b>TOTAL DA PROPOSTA:</b>", style_texto),
            Paragraph(
                f"{formatar_moeda(desconto_val)}<br/><br/>"
                f"<font size='11' color='#CA8A04'><b>{formatar_moeda(total_liquido)}</b></font>",
                style_texto_bold,
            ),
        ]
    ]
    t_totais = Table(totais_data, colWidths=[313, 110, 100])
    t_totais.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor("#F8FAFC")),
        ('BACKGROUND', (1, 0), (-1, -1), colors.HexColor("#FEFCE8")),
        ('BOX', (0, 0), (0, 1), 0.8, colors.HexColor("#E2E8F0")),
        ('BOX', (1, 0), (-1, -1), 0.8, colors.HexColor("#EAB308")),
        ('INNERGRID', (1, 0), (-1, -1), 0.5, colors.HexColor("#FEF08A")),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
    ]))
    story.append(t_totais)
    story.append(Spacer(1, 24))

    # 5. BLOCO DE ASSINATURAS E DE ACORDO
    assinaturas_data = [
        [
            Paragraph(
                "________________________________________________<br/>"
                f"<b>{empresa_nome}</b><br/>"
                "<font size='7' color='#71717A'>Departamento Comercial</font>",
                ParagraphStyle("Ass1", parent=style_texto, alignment=1),
            ),
            Paragraph(
                "________________________________________________<br/>"
                "<b>De Acordo do Cliente</b><br/>"
                "<font size='7' color='#71717A'>Assinatura / Data: ____/____/________</font>",
                ParagraphStyle("Ass2", parent=style_texto, alignment=1),
            ),
        ]
    ]
    t_ass = Table(assinaturas_data, colWidths=[261, 262])
    t_ass.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(KeepTogether(t_ass))

    class CanvasPersonalizado(PaginacaoCanvas):
        nome_empresa = empresa_nome

    doc.build(story, canvasmaker=CanvasPersonalizado)
    return buf.getvalue()


def salvar_pdf_orcamento_disco(orcamento: dict, empresa: dict | None = None) -> tuple[str, bytes]:
    """Gera e salva o PDF em disco, retornando (url_relativa, bytes)."""
    if not REPORTLAB_INSTALADO:
        raise RuntimeError(
            "O módulo 'reportlab' não está instalado no ambiente Python. "
            "Execute no terminal: pip install reportlab"
        )
    os.makedirs(DIR_UPLOADS_PDF, exist_ok=True)
    pdf_bytes = gerar_pdf_orcamento(orcamento, empresa=empresa)
    orc_id = orcamento.get("id") or int(datetime.now().timestamp())
    nome_arq = f"orcamento_{orc_id}_{int(datetime.now().timestamp())}.pdf"
    caminho_disco = os.path.join(DIR_UPLOADS_PDF, nome_arq).replace("\\", "/")
    with open(caminho_disco, "wb") as f:
        f.write(pdf_bytes)
    return f"/{caminho_disco}", pdf_bytes
