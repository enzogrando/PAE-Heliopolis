# Exploração de dados de saúde (SIH/SUS) — relatório curto

Período do estudo: 01/01/2021 a 31/12/2025. Nada foi alterado no dashboard nem commitado.

## Resultado em uma frase
Dá para montar uma série diária de internações por doenças do coração (CID I) e respiratórias (CID J) dos
**moradores da cidade de São Paulo** e cruzá-la com a temperatura do dashboard. **Não** dá para chegar a
Heliópolis só com os dados do SIH.

## Tarefas
1. **Arquivos.** O catálogo do PySUS tem 52 dos 60 meses de 2021–2025 (faltam 2021-01, 2022-07/08, 2023-04,
   2024-02/06/08/12). O FTP do DATASUS tem os 60 e publicou até **2026-08**. Os 8 meses ausentes foram obtidos
   do FTP (.dbc) e funcionaram.
2. **Colunas.** `RD` (AIH Reduzida) de SP: 113 colunas. Campos de interesse, todos presentes:
   `DT_INTER` (data da internação, AAAAMMDD), `DIAG_PRINC` (CID-10, 3–4 caracteres, ex. `J18`),
   `MUNIC_RES` (município de residência, IBGE 6 dígitos), `MUNIC_MOV` (município do hospital),
   `NASC`/`IDADE`+`COD_IDADE` (1=horas, 2=dias, 3=meses, 4=anos, 5=100+), `CEP` (8 dígitos).
   Cuidado: no PySUS, o grupo `SP` significa "Serviços Profissionais", não o estado; o estado vem do nome do
   arquivo (`RDSP...`).
3. **São Paulo = 355030** (código IBGE de 7 dígitos 3550308; o SIH usa 6). Média diária 2021–2025 de moradores
   da capital: I00–I99 = 167 internações/dia; J00–J99 = 148/dia (nenhum dia zerado). Tabela:
   `saidas/05_contagem_diaria.csv`.
4. **Custo.** Medido: 68 arquivos (2021-01 a 2026-08), 927 MB baixados, 7,3 min. Mês do espelho Parquet ≈ 4 s;
   mês via FTP ≈ 20 s. O resultado reduzido ocupa 15 MB (`saidas/reduzidos/`); os arquivos brutos foram apagados
   (sobram ~90 MB de cache do PySUS em `C:\Users\enzom\pysus`, fora do projeto). A tabela final (data, grupo, n)
   tem 3.652 linhas.
5. **Meses incompletos.** Dentro do período (até 2025-12) **não há queda anormal**: dez/2025 = 49.885 contra
   55.794 em out/2025 (queda sazonal de fim de ano, como em anos anteriores). Quedas existem só no fim da
   série publicada: **2026-08 (−27%)** e, em menor grau, 2026-06/07. Motivo: as internações chegam com atraso
   — só 60% aparecem no arquivo do próprio mês, 88% até 1 mês depois, 96% até 2 e 99% até 3. Como temos
   arquivos até 2026-08, 2025 está completo.

## O que dá para fazer
- Comparar dias quentes x não quentes (mesmo limiar do slider) em internações I e J, com defasagem de 0 a 3 dias.
- Separar por faixa etária (0–14, 15–64, 65+) — já está nos dados reduzidos.
- Reproduzir tudo com os scripts desta pasta; só a tabela pequena precisaria entrar no projeto.

## O que não dá
- **Heliópolis.** O CEP vem preenchido (100% válido nos moradores da capital), mas (a) 13% terminam em `000`
  (CEP genérico); (b) falta uma lista oficial de CEPs do bairro, que não temos; (c) mesmo com ela, o bairro tem
  da ordem de 0,4% da população da cidade (valor aproximado, de memória, a confirmar) — algo como 0–1
  internação por dia desses grupos, sem poder estatístico diário. Recomendo usar a cidade toda.
- Medir exposição individual, sintomas, sono ou qualidade de vida: o SIH só registra internações pagas pelo
  SUS (sem planos privados, sem atendimentos de UBS/UPA que não internaram).

## Riscos
- **Sazonalidade que não é calor.** Respiratórias sobem no outono/inverno (gripe, vírus sincicial); uma correlação
  simples com calor pode sair negativa. Precisa controlar mês/estação.
- **Tendência de alta** de 45 mil para 55 mil internações/mês (todas as causas) entre 2021 e 2025 e efeito da
  COVID em 2021: não é clima. Precisa remover tendência e dia da semana.
- **Dia da semana.** Coração: ~190/dia de segunda a quinta, 125 no sábado e 113 no domingo (internações
  eletivas). Respiratório varia menos.
- **Fim de ano.** 20–31/dez com cerca de 30% menos (provável feriado; não confirmado ano a ano).
- **Data de internação, não de início dos sintomas;** reapresentações antigas aparecem em arquivos novos
  (usamos `DT_INTER`, e só `IDENT=1` para não duplicar continuações).
- **Só o SUS** (viés de quem usa o SUS) e **só moradores da capital** que internaram em hospital de SP-estado.
- **Dependência técnica.** O PySUS 2.11.7 só funciona no Python 3.12 aqui (o 3.14 não instala); as funções de
  alto nível `pysus.ftp.sih()` e `list_files()` devolveram vazio, então usei a interface de baixo nível. O
  espelho do PySUS tem lacunas, o FTP não.
- **Linguagem.** Resultados serão associação, não causa; o dashboard já tem esse cuidado nos textos.

## Arquivos
`01_listar_arquivos.py`, `01b_comparar_ftp.py`, `02_um_mes.py`, `03_perfil_e_contagem_um_mes.py`,
`04_reduzir_para_contagens.py`, `05_contagem_mensal_e_diaria.py`; resultados em `saidas/`.
Ambiente: `.venv` (Python 3.12.10, PySUS 2.11.7).


## Teste de sinal (passo 1 do plano) — `06_teste_de_sinal.py` e `08_conferir_limiares.py`
Cruzamento da temperatura máxima diária ERA5 (mesma regra de dia válido do dashboard) com as internações diárias
de moradores da capital, em regressão de Poisson com controle de mês, ano, dia da semana e fim de ano.
Resultados: `saidas/06_resultado_sinal.csv` e `saidas/08_limiares_regressao.csv`.

**Correção:** a primeira versão deste relatório dizia "sem sinal relevante". Isso estava forte demais; a
conferência por limiar mostrou que o resultado depende de como se define "dia quente".

- **Limiares baixos (25 a 27 °C): aumento pequeno, estatisticamente distinguível de zero.** Dia com máxima
  >= 25 °C contra os demais: respiratório +4,8% (IC 95% +2,4% a +7,3%), coração +2,5% (+1,2% a +3,8%), com
  1.063 dias. Em 27 °C: respiratório +3,1%, coração +1,5% (intervalos começam perto de zero).
- **Limiares altos (28 °C ou mais): sem diferença detectável** (por exemplo, 30 °C: coração -0,7%,
  respiratório -0,3%), mas com poucos dias (251 em 30 °C; 74 em 32 °C) e intervalos largos (de cerca de -4% a +4%
  em 30 °C), que não descartam aumentos de alguns por cento.
- **Efeito por +1 °C na máxima (contínuo, atrasos de 0 a 3 dias):** entre -0,4% e +0,7%; sinais inconsistentes
  entre atrasos. Correlação simples sem controles: quase zero (-0,02 a +0,02).
- **Leitura honesta:** existe, no máximo, uma associação pequena (poucos por cento) entre dias moderadamente
  quentes e internações na cidade, mais clara para respiratórias; não há evidência de efeito forte nem de efeito
  específico de calor extremo (poucos dias). Não prova causa.
- **Cuidado:** são dezenas de comparações; resultados isolados podem ser acaso. O sinal em 25–26 °C pode refletir
  parte de outras coisas que variam com a estação (ex.: viroses de verão, outros fatores não controlados).
- **Por que o efeito é pequeno/difícil de ver:** SIH só registra internação (não UBS/UPA nem sintomas);
  temperatura máxima regional não é exposição individual; São Paulo raramente passa de 30 °C.
- **Validação do método do dashboard:** o dashboard usa um método mais simples (`saude.py`: dias quentes contra o
  esperado dos dias não quentes do mesmo ano, mês e dia da semana). Em 27 °C ele dá +2,2% (coração) e +3,9%
  (respiratório), próximo da regressão (+1,5% e +3,1%); em 30 °C ambos incluem o zero.
