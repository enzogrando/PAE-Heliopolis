"""Desenha o diagrama compartilhado; executado apenas na preparação documental."""
from pathlib import Path
from math import atan2, sin, cos
from PIL import Image, ImageDraw, ImageFont


def gerar():
    imagem = Image.new('RGB', (1800, 2090), 'white')
    d = ImageDraw.Draw(imagem)
    normal = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 30)
    negrito = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 32)
    pequeno = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 25)

    def caixa(r, titulo, linhas, cor='#EAF1F6'):
        d.rounded_rectangle(r, radius=15, fill=cor, outline='#486475', width=3)
        linhas = [titulo] + linhas
        y = (r[1]+r[3])/2 - ((len(linhas)-1)*40+34)/2
        for i,l in enumerate(linhas):
            d.text(((r[0]+r[2])/2,y),l,font=negrito if i==0 else normal,fill='#172D3B',anchor='mt')
            y += 40

    def seta(pontos, texto=None, pos=None):
        d.line(pontos,fill='#486475',width=5)
        x,y=pontos[-1]; px,py=pontos[-2]; a=atan2(y-py,x-px)
        d.polygon([(x,y),(x-18*cos(a-.45),y-18*sin(a-.45)),(x-18*cos(a+.45),y-18*sin(a+.45))],fill='#486475')
        if texto: d.text(pos,texto,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20) if texto in ('Resultados','Download') else pequeno,fill='#172D3B',anchor='mm')

    caixa((60,30,840,205),'API REST externa do Open-Meteo',[
        'HTTPS GET /v1/archive • modelo ERA5',
        'Coordenadas, datas e variáveis na URL',
        'Resposta JSON • timeout de 60 segundos'])
    caixa((960,30,1740,205),'Arquivo local do Open-Meteo',[
        'JSON ERA5 salvo tem prioridade',
        'Valores de origem e metadados da coleta',
        'A mesma fonte, disponível sem internet'])
    d.rounded_rectangle((30,335,1770,1280),radius=18,outline='#486475',width=4)
    d.text((1120,360),'APLICAÇÃO PYTHON • UM PROCESSO COM MÓDULOS',font=negrito,fill='#172D3B',anchor='mt')
    caixa((80,450,570,640),'E • Extrair',[
        'dados.py',
        'Ler a resposta JSON',
        'GET se não houver JSON'])
    caixa((655,450,1145,640),'T • Transformar',[
        'Pandas • validar e limpar',
        'UTC, grade e cobertura',
        'Preservar lacunas'])
    caixa((1230,450,1720,640),'L • Carregar',[
        'DataFrames em memória',
        'Sessão e cache Streamlit',
        'Sem data warehouse'])
    seta([(180,450),(180,205)],'GET',(115,275))
    seta([(430,205),(430,450)],'JSON',(485,275))
    seta([(1320,205),(1320,300),(550,300),(550,450)],'Leitura do disco',(1010,273))
    seta([(570,545),(655,545)])
    seta([(1145,545),(1230,545)])
    caixa((80,755,845,965),'Análise exploratória do calor',[
        'analise.py',
        'Dias, noites e sequências de calor',
        'Temperatura, umidade e perfil horário'])
    caixa((955,755,1720,965),'Apresentação e controle',[
        'app.py e painel.py • Streamlit',
        'Filtros, gráficos, cartões e tabelas',
        'Reexecução a cada interação'])
    seta([(1460,640),(1460,690),(460,690),(460,755)])
    seta([(845,855),(955,855)],'Resultados',(900,815))
    # Saúde: o módulo saude.py usa os dias quentes de analise.py e a tabela local de internações.
    caixa((80,1050,845,1240),'Calor e internações',[
        'saude.py e interpretacao.py',
        'Compara dias quentes com o esperado',
        'Intervalo de 95% por reamostragem'])
    seta([(460,965),(460,1050)],'Dias quentes',(580,1008))
    seta([(845,1145),(1000,1145),(1000,965)],'Resultados',(925,1115))
    caixa((80,1340,845,1520),'Tabela local de internações',[
        'dados_saude/internacoes_diarias_sp.csv',
        'Contagens por dia, doença (CID I e J) e idade',
        'Cidade de São Paulo, só SUS • 2021–2025'],cor='#F3EEDF')
    seta([(460,1340),(460,1240)],'Leitura do disco',(625,1310))
    caixa((955,1340,1720,1520),'Navegador do usuário',[
        'Acesso local ao Streamlit em :8501',
        'Exibe o painel e envia filtros'],cor='#E6EFE9')
    seta([(1160,965),(1160,1340)],'Interface',(1075,1080))
    seta([(1510,1340),(1510,965)],'Interações',(1595,1080))
    # Pipeline offline: roda uma vez no terminal e gera a tabela que o dashboard lê.
    d.rounded_rectangle((30,1590,1770,1900),radius=18,outline='#8A6D1F',width=4)
    d.text((520,1612),'PIPELINE OFFLINE DE SAÚDE • roda no terminal, fora do dashboard',font=negrito,fill='#172D3B',anchor='lt')
    caixa((80,1670,845,1870),'Scripts de exploracao_saude/',[
        '01 a 07 • Python 3.12 e PySUS',
        'Só moradores da capital (IBGE 355030)',
        'Reduz a contagens e apaga o arquivo bruto'],cor='#F3EEDF')
    caixa((955,1670,1720,1870),'DATASUS • SIH/SUS (AIH Reduzida)',[
        'PySUS: espelho Parquet (52 de 60 meses)',
        'FTP do DATASUS: arquivos .dbc (8 meses)',
        'Internações de 2021 a 2025'],cor='#F3EEDF')
    seta([(955,1770),(845,1770)],'Download',(900,1735))
    seta([(460,1670),(460,1520)],'Exporta a tabela',(625,1560))
    d.text((70,1930),'Persistência auxiliar pelo terminal',font=negrito,fill='#172D3B')
    d.text((70,1975),'gerar_relatorio.py → JSON, CSVs e TXT com origem, indicadores e qualidade da série ERA5',font=normal,fill='#172D3B')
    d.text((70,2030),'O dashboard não grava automaticamente essas saídas.',font=pequeno,fill='#172D3B')
    out=Path(__file__).resolve().parents[1]/'assets'/'arquitetura_projeto.png'
    out.parent.mkdir(exist_ok=True)
    imagem.save(out)
    return out


if __name__ == '__main__':
    print(gerar())
