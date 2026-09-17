#!/usr/bin/env python3
"""Gera docs/teams-andon.pdf — guia de configuração dos avisos no Teams."""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether,
                                ListFlowable, ListItem, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

# ---------------------------------------------------------------- fontes
FONTS = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("Sans", FONTS + "LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Sans-B", FONTS + "LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sans-I", FONTS + "LiberationSans-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Mono", FONTS + "LiberationMono-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Mono-B", FONTS + "LiberationMono-Bold.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans-I")

# ---------------------------------------------------------------- paleta
TEAL = colors.HexColor("#14505C")
TEAL2 = colors.HexColor("#2E747B")
BLUE = colors.HexColor("#1F5E9E")
AMBER = colors.HexColor("#C08A46")
TERRA = colors.HexColor("#A8462A")
INK = colors.HexColor("#0E1A20")
SOFT = colors.HexColor("#566B75")
LINE = colors.HexColor("#DDE6E9")
DIM = colors.HexColor("#E8EEF0")
SNOW = colors.HexColor("#F4F7F8")
WHITE = colors.white

PW, PH = A4
MARGIN = 20 * mm

# ---------------------------------------------------------------- estilos
def S(name, **kw):
    base = dict(name=name, fontName="Sans", fontSize=10, leading=15,
                textColor=INK, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(**base)

st = {
    "capa_titulo": S("capa_titulo", fontName="Sans-B", fontSize=30, leading=34,
                     textColor=WHITE),
    "capa_sub": S("capa_sub", fontSize=12.5, leading=18, textColor=colors.HexColor("#BFD6DA")),
    "h1": S("h1", fontName="Sans-B", fontSize=19, leading=23, textColor=TEAL,
            spaceBefore=4, spaceAfter=3),
    "h1num": S("h1num", fontName="Sans-B", fontSize=10, leading=12, textColor=TEAL2,
               spaceAfter=3),
    "h2": S("h2", fontName="Sans-B", fontSize=12.5, leading=16, textColor=INK,
            spaceBefore=13, spaceAfter=4),
    "body": S("body", spaceAfter=7),
    "lead": S("lead", fontSize=11, leading=17, textColor=SOFT, spaceAfter=9),
    "li": S("li", spaceAfter=5, leading=15),
    "sub": S("sub", fontSize=9, leading=13, textColor=SOFT, spaceAfter=6),
    "code": S("code", fontName="Mono", fontSize=8.4, leading=12.4, textColor=INK),
    "cell": S("cell", fontSize=9, leading=13),
    "cellb": S("cellb", fontName="Sans-B", fontSize=9, leading=13),
    "cellm": S("cellm", fontName="Mono", fontSize=8.2, leading=12),
    "callout": S("callout", fontSize=9.5, leading=14.5),
    "foot": S("foot", fontSize=8, leading=10, textColor=SOFT),
}

# ---------------------------------------------------------------- peças
class Rule(Flowable):
    """Fio horizontal fino."""
    def __init__(self, w, color=LINE, thick=0.7, pad=0):
        self.w, self.color, self.thick, self.pad = w, color, thick, pad
        self.height = thick + pad

    def wrap(self, aw, ah):
        return (self.w or aw, self.height)

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thick)
        self.canv.line(0, self.height - self.thick, self.w, self.height - self.thick)


class Diagram(Flowable):
    """Os três saltos do aviso, da tabela até o canal."""
    def __init__(self, w, h=69 * mm):
        self.w, self.height = w, h

    def wrap(self, aw, ah):
        return (self.w, self.height)

    def draw(self):
        c = self.canv
        cx = self.w / 2.0
        bw, bh = 62 * mm, 17 * mm
        gap = 9 * mm
        caixas = [
            (TEAL, "Supabase", "andon_events", "um chamado passou do tempo"),
            (BLUE, "Teams / Power Automate", "fluxo de webhook", "monta o cartão da mensagem"),
            (TEAL2, "Canal do Teams", "mensagem", "quem escala vê e cobra"),
        ]
        y = self.height - bh
        for i, (cor, titulo, meio, nota) in enumerate(caixas):
            x = cx - bw / 2.0
            c.setFillColor(cor)
            c.roundRect(x, y, bw, bh, 3 * mm, stroke=0, fill=1)
            c.setFillColor(WHITE)
            c.setFont("Sans-B", 9.5)
            c.drawCentredString(cx, y + bh - 6.2 * mm, titulo)
            c.setFont("Mono", 8)
            c.setFillColor(colors.HexColor("#CFE2E6"))
            c.drawCentredString(cx, y + bh - 10.6 * mm, meio)
            c.setFont("Sans", 7.6)
            c.drawCentredString(cx, y + bh - 14.4 * mm, nota)
            if i < len(caixas) - 1:
                c.setStrokeColor(colors.HexColor("#9FB6BC"))
                c.setLineWidth(1.1)
                c.line(cx, y - 1 * mm, cx, y - gap + 1.6 * mm)
                c.setFillColor(colors.HexColor("#9FB6BC"))
                p = c.beginPath()
                p.moveTo(cx, y - gap + 0.4 * mm)
                p.lineTo(cx - 1.5 * mm, y - gap + 2.6 * mm)
                p.lineTo(cx + 1.5 * mm, y - gap + 2.6 * mm)
                p.close()
                c.drawPath(p, stroke=0, fill=1)
            y -= bh + gap


def code(txt, w=None):
    """Bloco de código em caixa cinza."""
    linhas = [l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace(" ", "&nbsp;") for l in txt.strip("\n").split("\n")]
    p = Paragraph("<br/>".join(linhas), st["code"])
    t = Table([[p]], colWidths=[w or (PW - 2 * MARGIN)])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SNOW),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def callout(titulo, txt, cor=AMBER):
    p = Paragraph("<font name='Sans-B'>%s</font> %s" % (titulo, txt), st["callout"])
    t = Table([[p]], colWidths=[PW - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF6EE")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, cor),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def passos(itens, start=1):
    return ListFlowable(
        [ListItem(Paragraph(t, st["li"]), leftIndent=17, value=start + i)
         for i, t in enumerate(itens)],
        bulletType="1", start=start, leftIndent=17,
        bulletFontName="Sans-B", bulletFontSize=10, bulletColor=TEAL2,
    )


def bullets(itens):
    return ListFlowable(
        [ListItem(Paragraph(t, st["li"]), leftIndent=13) for t in itens],
        bulletType="bullet", bulletChar="•", leftIndent=13,
        bulletFontSize=10, bulletColor=TEAL2,
    )


def tabela(cabecalho, linhas, larguras, mono_cols=()):
    dados = [[Paragraph(h, st["cellb"]) for h in cabecalho]]
    for ln in linhas:
        dados.append([
            Paragraph(cel, st["cellm"] if i in mono_cols else st["cell"])
            for i, cel in enumerate(ln)
        ])
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DIM),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def secao(numero, titulo, resumo=None):
    out = [Paragraph(numero, st["h1num"]), Paragraph(titulo, st["h1"]),
           Rule(PW - 2 * MARGIN, TEAL2, 1.4, 6)]
    if resumo:
        out.append(Spacer(1, 5))
        out.append(Paragraph(resumo, st["lead"]))
    return out


# ---------------------------------------------------------------- páginas
def capa(canv, doc):
    canv.saveState()
    canv.setFillColor(TEAL)
    canv.rect(0, PH - 118 * mm, PW, 118 * mm, stroke=0, fill=1)
    # sinal da marca: quadrado com os raios vazados
    canv.setFillColor(WHITE)
    ox, oy, sz = MARGIN, PH - 40 * mm, 13 * mm
    canv.rect(ox, oy, sz, sz, stroke=0, fill=1)
    canv.setFillColor(TEAL)
    cx, cy = ox + sz * 0.34, oy + sz * 0.47
    import math
    for ang, wid in ((100, 5), (65, 3.4), (20, 3), (-8, 4.6), (-40, 3), (-75, 3.6),
                     (-110, 4.2), (-145, 3), (170, 3.6), (140, 4)):
        a = math.radians(ang)
        for d in (-1, 1):
            b = math.radians(ang + d * wid)
            p = canv.beginPath()
            p.moveTo(cx, cy)
            p.lineTo(cx + math.cos(a) * sz, cy + math.sin(a) * sz)
            p.lineTo(cx + math.cos(b) * sz, cy + math.sin(b) * sz)
            p.close()
            canv.drawPath(p, stroke=0, fill=1)
    canv.setFillColor(WHITE)
    canv.setFont("Sans-B", 12)
    canv.drawString(ox + sz + 5 * mm, oy + sz - 6.2 * mm, "S.T.A.R.")
    canv.setFont("Sans", 6.6)
    canv.setFillColor(colors.HexColor("#BFD6DA"))
    canv.drawString(ox + sz + 5.3 * mm, oy + sz - 10.4 * mm, "L A B O R A T O R I E S")

    canv.setFillColor(WHITE)
    canv.setFont("Sans-B", 30)
    canv.drawString(MARGIN, PH - 74 * mm, "Avisos de chamado")
    canv.drawString(MARGIN, PH - 86 * mm, "no Microsoft Teams")
    canv.setFont("Sans", 12)
    canv.setFillColor(colors.HexColor("#BFD6DA"))
    canv.drawString(MARGIN, PH - 99 * mm,
                    "Screenplay 2.0   \u00b7   guia de configura\u00e7\u00e3o")
    canv.setFont("Sans", 11)
    canv.drawString(MARGIN, PH - 106 * mm, "Do banco de dados ao canal, passo a passo.")
    canv.restoreState()


def corrida(canv, doc):
    canv.saveState()
    canv.setStrokeColor(LINE)
    canv.setLineWidth(0.6)
    canv.line(MARGIN, PH - MARGIN + 6 * mm, PW - MARGIN, PH - MARGIN + 6 * mm)
    canv.setFont("Sans", 7.6)
    canv.setFillColor(SOFT)
    canv.drawString(MARGIN, PH - MARGIN + 8.4 * mm, "Screenplay 2.0")
    canv.drawRightString(PW - MARGIN, PH - MARGIN + 8.4 * mm,
                         "Avisos de chamado no Microsoft Teams")
    canv.line(MARGIN, 15 * mm, PW - MARGIN, 15 * mm)
    canv.setFont("Sans", 7.6)
    canv.drawRightString(PW - MARGIN, 10.5 * mm, str(canv.getPageNumber()))
    canv.drawString(MARGIN, 10.5 * mm, "A URL do fluxo é uma credencial: não compartilhe.")
    canv.restoreState()


def build(saida):
    doc = BaseDocTemplate(saida, pagesize=A4,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=22 * mm,
                          title="Avisos de chamado no Microsoft Teams",
                          author="Matheus Marcondes",
                          subject="Screenplay 2.0 — configuração do andon no Teams")
    largura = PW - 2 * MARGIN
    doc.addPageTemplates([
        # a faixa da capa ocupa os 118 mm de cima; o quadro comeca abaixo dela
        PageTemplate(id="capa", onPage=capa, frames=[
            Frame(MARGIN, 22 * mm, largura, PH - 118 * mm - 8 * mm - 22 * mm, id="capa-f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)]),
        PageTemplate(id="corrida", onPage=corrida, frames=[
            Frame(MARGIN, 22 * mm, largura, PH - MARGIN - 30 * mm, id="corrida-f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)]),
    ])
    doc.build(conteudo(largura))


# ---------------------------------------------------------------- conteúdo
CARTAO = """
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "Container",
      "style": "emphasis",
      "bleed": true,
      "items": [
        { "type": "TextBlock", "spacing": "None", "size": "Small",
          "weight": "Bolder", "isSubtle": true,
          "text": "@{triggerBody()?['evento_label']}" },
        { "type": "TextBlock", "spacing": "None", "size": "ExtraLarge",
          "weight": "Bolder",
          "text": "@{triggerBody()?['tipo_label']}" },
        { "type": "TextBlock", "spacing": "None", "size": "Medium",
          "text": "Mesa @{triggerBody()?['mesa_label']}" }
      ]
    },
    { "type": "TextBlock", "spacing": "Medium", "wrap": true,
      "text": "@{triggerBody()?['resumo']}" },
    {
      "type": "FactSet",
      "facts": [
        { "title": "Etapa",       "value": "@{triggerBody()?['etapa']}" },
        { "title": "Aciona",      "value": "@{triggerBody()?['destino']}" },
        { "title": "Aberto há",    "value": "@{triggerBody()?['minutos_aberto']} min" },
        { "title": "Aviso número", "value": "@{triggerBody()?['aviso_numero']}" }
      ]
    }
  ],
  "actions": [
    { "type": "Action.OpenUrl", "title": "Abrir o painel",
      "url": "https://screenplay.marcondes.dev/#andon" }
  ]
}
"""

SCHEMA = """
{
  "type": "object",
  "properties": {
    "evento":         { "type": "string" },
    "evento_label":   { "type": "string" },
    "id":             { "type": "string" },
    "tipo":           { "type": "string" },
    "tipo_label":     { "type": "string" },
    "destino":        { "type": "string" },
    "cor":            { "type": "string" },
    "mesa":           { "type": ["integer", "null"] },
    "mesa_label":     { "type": "string" },
    "etapa":          { "type": "string" },
    "aberto_em":      { "type": "string" },
    "minutos_aberto": { "type": "integer" },
    "aviso_numero":   { "type": "integer" },
    "titulo":         { "type": "string" },
    "resumo":         { "type": "string" }
  }
}
"""


def conteudo(largura):
    f = []
    A = f.append

    # ---------------------------------------------------------- capa
    A(Spacer(1, 4 * mm))
    A(Diagram(largura))
    A(Spacer(1, 10 * mm))
    A(Paragraph("O que você vai ter no final", st["h2"]))
    A(Paragraph(
        "Um chamado de andon que fica aberto além do tempo que você definir vira uma mensagem "
        "num canal do Teams, com o tipo, a mesa, a etapa e há quantos minutos ninguém atendeu. "
        "Os painéis do andon continuam sendo o lugar de trabalhar a fila. O Teams entra como "
        "<b>escalonamento</b>: ele cobra o que passou batido.", st["body"]))
    A(Paragraph(
        "Opcionalmente, também dá para avisar já na abertura de cada chamado, e repetir o aviso "
        "de tantos em tantos minutos enquanto ele seguir aberto. Tudo isso é configurado por "
        "tipo de chamado, no banco.", st["body"]))
    A(Spacer(1, 3 * mm))
    A(Paragraph("Tempo estimado: 25 a 40 minutos, a primeira vez.", st["sub"]))
    A(NextPageTemplate("corrida"))
    A(PageBreak())

    # ---------------------------------------------------------- antes
    A(Spacer(1, 2 * mm))
    f.extend(secao("Antes de começar", "O que ter em mão",
                   "Três acessos e uma decisão. Se faltar algum acesso, resolva isso primeiro: "
                   "no meio do caminho fica pior."))
    A(Paragraph("Acessos", st["h2"]))
    A(bullets([
        "<b>Microsoft Teams</b>, com permissão para criar um fluxo de trabalho no canal que vai "
        "receber os avisos. Se a sua organização bloqueia o app Workflows, é aqui que o plano "
        "para, e nenhum passo seguinte resolve.",
        "<b>Power Automate</b>, em <font name='Mono'>make.powerautomate.com</font>, com a mesma "
        "conta do Teams. Não precisa de licença paga para o que este guia usa.",
        "<b>Supabase</b>, o projeto do Screenplay, com acesso ao SQL Editor e a Database > "
        "Extensions.",
    ]))
    A(Paragraph("A decisão", st["h2"]))
    A(Paragraph(
        "Um canal só para todos os chamados, ou um canal por perfil? O guia monta o caminho de "
        "um canal só, porque é o mais simples e o que costuma bastar. Se você quiser separar, a "
        "seção 4 explica o que muda: é repetir a Parte 1 para cada canal.", st["body"]))
    A(Spacer(1, 2 * mm))
    A(callout("Sobre a URL.",
              "O fluxo do Teams é acionado por uma URL longa e secreta. Quem tem essa URL "
              "consegue postar no canal. Ela vive só no banco de dados, com a leitura fechada "
              "para a chave pública do sistema, e nunca entra no arquivo que as TVs baixam. "
              "Não mande essa URL por e-mail ou chat, e não coloque num repositório.", TERRA))
    A(Spacer(1, 6 * mm))
    A(Paragraph("A ordem das partes", st["h2"]))
    A(tabela(
        ["Parte", "Onde", "O que você faz"],
        [["1", "Teams", "Cria o fluxo que recebe o aviso e copia a URL dele."],
         ["2", "Power Automate", "Dá forma à mensagem que vai aparecer no canal."],
         ["3", "Supabase", "Roda a migração, cola a URL e testa."],
         ["4", "Supabase", "Ajusta tempos, repetição e quais tipos avisam."],
         ["5", "Qualquer", "Confere, e resolve o que não funcionou."]],
        [16 * mm, 33 * mm, largura - 49 * mm]))
    A(PageBreak())

    # ---------------------------------------------------------- parte 1
    f.extend(secao("Parte 1", "Teams: criar o fluxo e pegar a URL",
                   "No fim desta parte você tem uma URL. É só o que a Parte 3 precisa."))
    A(passos([
        "Abra o <b>Microsoft Teams</b> no computador. O app de celular não mostra os fluxos de "
        "trabalho.",
        "Vá até o <b>canal</b> que vai receber os avisos. Se ele ainda não existe, crie agora. "
        "Vale a pena ser um canal dedicado: os avisos são repetitivos e atrapalham num canal de "
        "conversa.",
        "Passe o mouse no nome do canal, clique nos <b>três pontos</b> (Mais opções) e escolha "
        "<b>Fluxos de trabalho</b>. Em inglês, <b>Workflows</b>.<br/>"
        "<font size='9' color='#566B75'>Se não aparecer, abra <b>Aplicativos</b> na barra "
        "lateral do Teams, procure por <b>Workflows</b> e adicione. Depois volte ao canal.</font>",
        "Na busca de modelos, digite <b>webhook</b>. Escolha o modelo <b>Postar em um canal "
        "quando uma solicitação de webhook for recebida</b>. Em inglês, <b>Post to a channel "
        "when a webhook request is received</b>.",
        "Dê um nome ao fluxo. Sugestão: <font name='Mono'>Screenplay - Andon</font>. Esse nome "
        "vai te ajudar a achar o fluxo na Parte 2.",
        "A tela mostra as <b>conexões</b> usadas. Se o Microsoft Teams aparecer com um aviso, "
        "clique para entrar com a sua conta. Depois avance.",
        "Escolha a <b>Equipe</b> e o <b>Canal</b> de destino. Avance.",
        "Clique em <b>Adicionar fluxo de trabalho</b> (Add workflow).",
        "A tela final mostra uma <b>URL do fluxo</b>. Você pode copiar, mas <b>não é essa que "
        "vale</b>: ela ainda vai mudar na Parte 2. Pode fechar sem medo.",
    ]))
    A(Spacer(1, 3 * mm))
    A(callout("Por que a URL ainda vai mudar.",
              "A URL carrega a assinatura que autoriza a chamada, e essa assinatura só entra "
              "nela quando o gatilho é liberado para quem não está logado. Isso é o primeiro "
              "passo da Parte 2. Copiar a URL antes disso é copiar uma que não vai funcionar.",
              TERRA))
    A(Spacer(1, 6 * mm))
    A(Paragraph("Como a URL se parece", st["h2"]))
    A(code("https://<região>.api.powerplatform.com/powerautomate/automations/direct\n"
           "/workflows/8f3c.../triggers/manual/paths/invoke?api-version=1\n"
           "&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=QnVfLW...", largura))
    A(Paragraph("A sua vai ser diferente e mais longa. O domínio pode variar: o antigo "
                "<font name='Mono'>logic.azure.com</font> foi aposentado em favor de "
                "<font name='Mono'>api.powerplatform.com</font>. Copie o que a tela mostrar, "
                "inteiro, do <font name='Mono'>https</font> ao último caractere.", st["sub"]))
    A(PageBreak())

    # ---------------------------------------------------------- parte 2
    f.extend(secao("Parte 2", "Power Automate: dar forma à mensagem",
                   "O modelo do Teams vem esperando um formato de mensagem que não é o nosso. "
                   "Aqui você troca o cartão e libera o gatilho."))
    A(passos([
        "Abra <font name='Mono'>make.powerautomate.com</font> no navegador, com a <b>mesma "
        "conta</b> do Teams.",
        "No menu da esquerda, clique em <b>Meus fluxos</b> (My flows).",
        "Ache <font name='Mono'>Screenplay - Andon</font> na lista. Clique no nome e depois em "
        "<b>Editar</b> (Edit).",
        "O fluxo tem duas caixas: o gatilho <b>Quando uma solicitação de webhook do Teams é "
        "recebida</b> e a ação <b>Postar cartão em um chat ou canal</b>.",
    ]))
    A(Spacer(1, 4 * mm))
    A(Paragraph("2.1 &nbsp; Liberar o gatilho e pegar a URL", st["h2"]))
    A(passos([
        "Clique na caixa do <b>gatilho</b>, a de cima. Fique na aba <b>Parâmetros</b>.",
        "Em <b>Quem pode disparar o fluxo?</b>, abra a lista e escolha <b>Alguém</b>.",
        "Clique em <b>Salvar</b>.",
        "Volte na caixa do gatilho. Agora copie a <b>URL do HTTP POST</b>, com o botão de "
        "copiar ao lado do campo. <b>É esta a URL</b> que vai para o banco, na Parte 3.",
    ], start=5))
    A(Spacer(1, 3 * mm))
    A(callout("Alguém quer dizer Anyone.",
              "A tradução da Microsoft para o português ficou estranha. A lista mostra quatro "
              "linhas: <b>Alguém</b>, <i>Qualquer usuário no meu locatário</i>, <i>Usuários "
              "específicos do meu locatário</i> e <i>Inserir valor personalizado</i>. "
              "<b>Alguém</b> é o Anyone, e é a única que serve. As duas do locatário exigem que "
              "quem chama esteja logado na sua organização, e o Supabase não está logado em "
              "nada: ele tomaria um erro de autenticação e o aviso nunca chegaria, sem nenhuma "
              "mensagem de erro visível no Teams.", TERRA))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "Se a lista não aceitar <b>Alguém</b>, ou o fluxo se recusar a salvar depois de "
        "escolher, é política da sua organização barrando gatilhos anônimos. Nesse caso não há "
        "contorno pelo lado do Supabase, e o caminho é falar com quem administra o Power "
        "Platform.", st["body"]))
    A(Spacer(1, 6 * mm))
    A(Paragraph("2.2 &nbsp; Trocar o cartão", st["h2"]))
    A(passos([
        "Clique na caixa da ação <b>Postar cartão em um chat ou canal</b>.",
        "Confira se <b>Postar como</b> está em <b>Flow bot</b> e se <b>Postar em</b>, a "
        "<b>Equipe</b> e o <b>Canal</b> são os que você escolheu na Parte 1.",
        "No campo <b>Adaptive Card</b> há um JSON de exemplo. <b>Apague tudo</b> e cole o "
        "cartão da página seguinte no lugar.",
        "Se o endereço do seu painel não for o do último item do cartão, troque a URL dentro de "
        "<font name='Mono'>Action.OpenUrl</font>.",
        "Clique em <b>Salvar</b>.",
    ], start=9))
    A(Spacer(1, 4 * mm))
    A(Paragraph(
        "O cartão usa expressões como <font name='Mono'>@{triggerBody()?['titulo']}</font>. "
        "Elas pegam os campos que o banco manda. Você não precisa montar nada com o seletor de "
        "conteúdo dinâmico: cole o JSON e salve.", st["body"]))
    A(PageBreak())

    # ---------------------------------------------------------- cartão
    f.extend(secao("Parte 2", "O cartão, para copiar",
                   "Cole isto inteiro no campo Adaptive Card da ação de postar."))
    A(code(CARTAO, largura))
    A(Spacer(1, 5 * mm))
    A(Paragraph("Mudanças fáceis, se quiser", st["h2"]))
    A(tabela(
        ["Para", "Troque"],
        [["A faixa do topo ficar vermelha",
          "<font name='Mono'>\"style\": \"emphasis\"</font> por "
          "<font name='Mono'>\"attention\"</font>"],
         ["A faixa ficar azul",
          "<font name='Mono'>\"emphasis\"</font> por <font name='Mono'>\"accent\"</font>"],
         ["Tirar o botão do painel",
          "apague o bloco <font name='Mono'>\"actions\"</font> inteiro, e a vírgula antes dele"],
         ["Mostrar a hora de abertura",
          "acrescente um fato com <font name='Mono'>@{triggerBody()?['aberto_em']}</font>"]],
        [56 * mm, largura - 56 * mm]))
    A(PageBreak())

    # ---------------------------------------------------------- parte 3
    f.extend(secao("Parte 3", "Supabase: ligar o banco",
                   "Duas extensões, uma migração, a URL e um teste."))
    A(Paragraph("3.1 &nbsp; Ligar as extensões", st["h2"]))
    A(passos([
        "Abra o painel do Supabase e escolha o projeto do Screenplay.",
        "No menu, vá em <b>Database</b> e depois em <b>Extensions</b>.",
        "Procure <font name='Mono'>pg_net</font> e ligue. É o que permite ao banco fazer uma "
        "chamada HTTP.",
        "Procure <font name='Mono'>pg_cron</font> e ligue. É o que faz a verificação rodar de "
        "minuto em minuto.",
    ]))
    A(Spacer(1, 5 * mm))
    A(Paragraph("3.2 &nbsp; Rodar a migração", st["h2"]))
    A(passos([
        "No menu, vá em <b>SQL Editor</b> e clique em <b>New query</b>.",
        "Abra o arquivo <font name='Mono'>supabase/migrations/0006_andon_teams.sql</font> do "
        "repositório, copie o conteúdo inteiro e cole no editor.",
        "Clique em <b>Run</b>. Deve terminar sem erro, mostrando algumas linhas de resultado no "
        "fim.",
    ], start=5))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "A migração cria a tabela de configuração, as funções de envio e a tarefa de minuto em "
        "minuto. Já nasce <b>desligada</b> e sem URL, então nada é enviado até você mandar. "
        "Rodar o arquivo de novo é seguro.", st["body"]))
    A(Spacer(1, 5 * mm))
    A(Paragraph("3.3 &nbsp; Colar a URL e ligar", st["h2"]))
    A(Paragraph("Em uma nova query, troque o texto entre as aspas pela URL da Parte 1:",
                st["body"]))
    A(code("""
update andon_notify_config
   set webhook_url = 'COLE_AQUI_A_URL_DO_FLUXO',
       enabled     = true
 where tipo in ('falta_material','qualidade','inspecao','assistente');
""", largura))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "Isso liga os quatro tipos de chamado no mesmo canal. Para começar com um só tipo, "
        "deixe apenas ele dentro do <font name='Mono'>in (...)</font>.", st["sub"]))
    A(PageBreak())

    # ---------------------------------------------------------- teste
    f.extend(secao("Parte 3", "Testar antes de confiar",
                   "O teste manda um chamado de mentira. Não cria nada em andon_events e não "
                   "aparece em nenhum painel."))
    A(Paragraph("3.4 &nbsp; Mandar um cartão de teste", st["h2"]))
    A(code("select andon_notify_test('falta_material');", largura))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "Deve chegar um cartão no canal em poucos segundos, escrito "
        "<b>Teste de configuração</b> e <b>Mesa 07</b>. Se chegou, o caminho inteiro está de pé "
        "e você pode ir para a Parte 4.", st["body"]))
    A(Spacer(1, 4 * mm))
    A(Paragraph("3.5 &nbsp; Ver o que o Teams respondeu", st["h2"]))
    A(code("""
select status_code, content, created
  from net._http_response
 order by created desc
 limit 5;
""", largura))
    A(Spacer(1, 3 * mm))
    A(tabela(
        ["Resposta", "O que significa"],
        [["202 ou 200", "Aceito. O fluxo recebeu e vai postar."],
         ["401 ou 403", "O gatilho não está em <b>Alguém</b>. Volte ao passo 6."],
         ["404", "A URL está incompleta, é a antiga do wizard, ou o fluxo foi apagado. "
                  "Copie a URL de novo pelo gatilho."],
         ["400", "O fluxo recebeu mas rejeitou o corpo. Veja o histórico de execuções na "
                 "seção 5."],
         ["nada listado", "O <font name='Mono'>pg_net</font> não chegou a enviar. Confirme que "
                          "a extensão está ligada."]],
        [30 * mm, largura - 30 * mm]))
    A(Spacer(1, 5 * mm))
    A(Paragraph("3.6 &nbsp; Conferir o estado geral", st["h2"]))
    A(code("select * from andon_notify_status;", largura))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "Uma linha por tipo de chamado: se está ligado, se tem URL, o começo da URL para você "
        "reconhecer qual é, os tempos configurados, quantos chamados daquele tipo estão abertos "
        "agora e quando saiu o último aviso. A URL nunca aparece inteira.", st["body"]))
    A(PageBreak())

    # ---------------------------------------------------------- parte 4
    f.extend(secao("Parte 4", "Ajustar o comportamento",
                   "Tudo mora na tabela andon_notify_config, uma linha por tipo de chamado. "
                   "Mudanças valem no minuto seguinte, sem reiniciar nada."))
    A(tabela(
        ["Coluna", "O que faz"],
        [["enabled",
          "Liga e desliga aquele tipo sem perder a URL."],
         ["webhook_url",
          "A URL do fluxo no Teams. Vazia, nada é enviado."],
         ["escalate_after_seconds",
          "Quantos segundos um chamado pode ficar aberto antes de virar aviso. Padrão: 180 "
          "para falta de material, 300 para os outros."],
         ["notify_on_open",
          "Avisar já na abertura, além do escalonamento. Vem desligado."],
         ["repeat_after_seconds",
          "Repetir o aviso a cada tanto, enquanto o chamado seguir aberto. Vazio, avisa uma vez "
          "e para. Mínimo de 60."],
         ["label, destino, cor",
          "O texto e a cor que aparecem no cartão. Mude se quiser outro nome."]],
        [44 * mm, largura - 44 * mm], mono_cols=(0,)))
    A(Spacer(1, 6 * mm))
    A(Paragraph("Receitas", st["h2"]))
    A(KeepTogether([
        Paragraph("<b>Escalonar mais rápido a falta de material</b>, em dois minutos:", st["body"]),
        code("update andon_notify_config set escalate_after_seconds = 120\n"
             " where tipo = 'falta_material';", largura)]))
    A(Spacer(1, 4 * mm))
    A(Paragraph("<b>Cobrar de cinco em cinco minutos</b> enquanto ninguém atende:", st["body"]))
    A(code("update andon_notify_config set repeat_after_seconds = 300\n"
           " where tipo = 'falta_material';", largura))
    A(Spacer(1, 4 * mm))
    A(Paragraph("<b>Avisar também na abertura</b> de cada chamado:", st["body"]))
    A(code("update andon_notify_config set notify_on_open = true\n"
           " where tipo = 'falta_material';", largura))
    A(Spacer(1, 4 * mm))
    A(Paragraph("<b>Desligar um tipo</b>, guardando a URL para depois:", st["body"]))
    A(code("update andon_notify_config set enabled = false where tipo = 'assistente';", largura))
    A(Spacer(1, 4 * mm))
    A(Paragraph("<b>Desligar tudo de uma vez</b>, inclusive a verificação de minuto em minuto:",
                st["body"]))
    A(code("update andon_notify_config set enabled = false;\n"
           "select cron.unschedule('andon-notify');", largura))
    A(Spacer(1, 3 * mm))
    A(Paragraph("Para religar depois, rode a migração de novo.", st["sub"]))
    A(PageBreak())

    # ---------------------------------------------------------- canais
    f.extend(secao("Parte 4", "Um canal por perfil",
                   "Se cada time preferir o seu canal, o desenho é o mesmo repetido."))
    A(passos([
        "Repita a <b>Parte 1</b> uma vez para cada canal, criando um fluxo por canal. Dê nomes "
        "que você reconheça, como <font name='Mono'>Screenplay - Material</font>.",
        "Repita a <b>Parte 2</b> em cada fluxo novo. O mesmo cartão serve para todos.",
        "No banco, rode um update por tipo, cada um com a URL do seu canal:",
    ]))
    A(Spacer(1, 2 * mm))
    A(code("""
update andon_notify_config set webhook_url = 'URL_DO_CANAL_MATERIAL',  enabled = true
 where tipo = 'falta_material';

update andon_notify_config set webhook_url = 'URL_DO_CANAL_QUALIDADE', enabled = true
 where tipo = 'qualidade';

update andon_notify_config set webhook_url = 'URL_DO_CANAL_INSPECAO',  enabled = true
 where tipo = 'inspecao';

update andon_notify_config set webhook_url = 'URL_DO_CANAL_ASSIST',    enabled = true
 where tipo = 'assistente';
""", largura))
    A(Spacer(1, 5 * mm))
    A(Paragraph(
        "Nada mais muda. Cada tipo de chamado já carrega a sua própria URL, então o banco manda "
        "cada aviso para o canal certo sozinho.", st["body"]))
    A(Spacer(1, 4 * mm))
    A(callout("Uma sugestão de uso.",
              "Vale ligar o escalonamento em todos os tipos mas deixar o aviso na abertura "
              "desligado. Os painéis do andon já avisam quem precisa agir, com som. Se o Teams "
              "repetir tudo, as pessoas param de olhar, e aí o escalonamento também perde "
              "efeito."))
    A(PageBreak())

    # ---------------------------------------------------------- parte 5
    f.extend(secao("Parte 5", "Conferir e resolver",
                   "Onde olhar quando não chega o que deveria."))
    A(Paragraph("Recuperar a URL do fluxo", st["h2"]))
    A(passos([
        "Em <font name='Mono'>make.powerautomate.com</font>, abra <b>Meus fluxos</b> e clique "
        "no fluxo.",
        "Clique em <b>Editar</b> e depois na caixa do gatilho.",
        "A URL aparece num campo de leitura, com um botão de copiar ao lado.",
    ]))
    A(Spacer(1, 5 * mm))
    A(Paragraph("Ver o que o fluxo recebeu", st["h2"]))
    A(passos([
        "Abra o fluxo em <b>Meus fluxos</b>, sem entrar em Editar.",
        "Na lista <b>Histórico de execuções</b> (Run history), clique na execução mais recente.",
        "Clique no gatilho para abrir as <b>Saídas</b> (Outputs). O <b>Corpo</b> (Body) mostra "
        "exatamente o JSON que o banco mandou.",
    ]))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "Se o corpo estiver ali com todos os campos mas o cartão chegou vazio, as expressões do "
        "cartão não estão achando os campos. Nesse caso, acrescente uma ação <b>Analisar JSON</b> "
        "logo depois do gatilho, com o esquema da página seguinte, e troque no cartão "
        "<font name='Mono'>triggerBody()</font> pelo conteúdo dinâmico que a nova ação passa a "
        "oferecer.", st["body"]))
    A(Spacer(1, 5 * mm))
    A(Paragraph("Ver se a verificação está rodando", st["h2"]))
    A(code("""
select jobname, schedule, active from cron.job;

select status, return_message, start_time
  from cron.job_run_details
 order by start_time desc
 limit 10;
""", largura))
    A(Spacer(1, 5 * mm))
    A(Paragraph("Não chega nada: a lista de checagem", st["h2"]))
    A(tabela(
        ["Confira", "Como"],
        [["O gatilho está em <b>Alguém</b>",
          "Parte 2, passo 6. É a causa mais comum."],
         ["A URL foi copiada depois disso",
          "A assinatura só entra na URL quando o gatilho é liberado"],
         ["O tipo está ligado e tem URL",
          "<font name='Mono'>select * from andon_notify_status;</font>"],
         ["As extensões estão ligadas",
          "Database &gt; Extensions: <font name='Mono'>pg_net</font> e "
          "<font name='Mono'>pg_cron</font>"],
         ["A tarefa está agendada",
          "<font name='Mono'>select * from cron.job;</font> deve trazer "
          "<font name='Mono'>andon-notify</font>"],
         ["O chamado passou do tempo",
          "Um chamado de 1 minuto não escala se o tempo é 3 minutos"],
         ["O aviso não foi enviado já",
          "Com <font name='Mono'>repeat_after_seconds</font> vazio, cada chamado avisa uma vez "
          "só"],
         ["A resposta do envio",
          "<font name='Mono'>select status_code, content from net._http_response order by "
          "created desc limit 5;</font>"]],
        [52 * mm, largura - 52 * mm]))
    A(PageBreak())

    # ---------------------------------------------------------- referência
    f.extend(secao("Referência", "O que o banco manda",
                   "Os campos vão prontos para uso: o cartão só referencia, não calcula."))
    A(tabela(
        ["Campo", "Exemplo", "O que é"],
        [["evento", "escalonamento", "abertura, escalonamento ou teste"],
         ["evento_label", "Sem atendimento", "o mesmo, em texto de cartão"],
         ["tipo", "falta_material", "o tipo, como está no banco"],
         ["tipo_label", "Falta de Material", "o nome que aparece no painel"],
         ["destino", "Material Handler", "quem o chamado aciona"],
         ["mesa", "7", "número da mesa, ou vazio"],
         ["mesa_label", "07", "o mesmo, com dois dígitos"],
         ["etapa", "SVE", "a supervisão da operadora"],
         ["minutos_aberto", "9", "há quanto tempo está aberto"],
         ["aviso_numero", "2", "quantas vezes este chamado já avisou"],
         ["titulo", "Falta de Material · Mesa 07", "linha pronta para o topo do cartão"],
         ["resumo", "SVE · aberto há 9 min sem atend.", "linha pronta para o corpo"],
         ["cor", "#C08A46", "a cor do tipo no painel"],
         ["aberto_em", "2026-09-17T15:23:28Z", "quando o chamado abriu"],
         ["id", "a8b21e6f-...", "o chamado em andon_events"]],
        [30 * mm, 46 * mm, largura - 76 * mm], mono_cols=(0, 1)))
    A(Spacer(1, 6 * mm))
    A(KeepTogether([
        Paragraph("Esquema para a ação Analisar JSON", st["h2"]),
        Paragraph("Só é necessário no caso descrito na seção 5.", st["sub"]),
        code(SCHEMA, largura),
    ]))
    A(Spacer(1, 6 * mm))
    A(Rule(largura, LINE, 0.7, 4))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "<b>Screenplay</b> é um projeto pessoal e de código aberto, criado por iniciativa "
        "própria, sob licença MIT. Não é produto oficial de nenhuma empresa e não se integra "
        "a sistemas corporativos. S.T.A.R. Laboratories é uma marca fictícia, usada aqui "
        "como exemplo de identidade visual. Desenvolvido por Matheus Marcondes.", st["sub"]))
    return f


if __name__ == "__main__":
    import sys
    build(sys.argv[1])
    print("gerado:", sys.argv[1])
