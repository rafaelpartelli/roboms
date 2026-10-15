# Tarefa agendada: Radar Saúde Pública (newsletter)

Cópia de referência da tarefa agendada do Claude que monitora notícias e indicadores de saúde pública e envia a newsletter por e-mail. A tarefa roda na nuvem do Claude (não no GitHub); este arquivo serve para documentação, versionamento e recriação, se necessário.

| Campo | Valor |
|---|---|
| Nome | Monitoramento de notícias e indicadores de saúde pública |
| Identificador | trig_01Hq9hecqQBDnjuCvCVTGpm5 |
| Agenda | Segunda, quarta e sexta às 06:53 (America/Sao_Paulo) |
| Modelo | claude-sonnet-5-5 |
| Conectores | Gmail, Google Drive, Google Calendar, Claude Docs, Hostinger |
| Entrega | E-mail HTML para rafael@partelli.pro |
| Cópia feita em | 15/10/2026 |

## Instrução completa da tarefa

```text
Você está executando uma tarefa agendada para Rafael Tartaglias Partelli, gestor e consultor de saúde pública (mais de 20 anos de experiência no SUS, nas esferas municipal, estadual e federal). Esta execução ocorre às segundas, quartas e sextas, cedo pela manhã (horário de Brasília). Ninguém estará disponível para responder perguntas: tome decisões razoáveis e declare as premissas na própria newsletter.

REGRA DE INÍCIO (verifique primeiro, com o comando date)
O envio só começa na segunda-feira 05/10/2026. Se a data atual (horário de Brasília) for anterior a 05/10/2026, NÃO pesquise e NÃO envie nada: encerre informando "Início programado para 05/10/2026". A primeira edição (05/10/2026) deve cobrir desde 01/10/2026.

OBJETIVO
Monitorar notícias e indicadores de saúde pública relevantes para a gestão do SUS e entregar uma NEWSLETTER por e-mail, com leitura dinâmica e links para o acesso às matérias originais, com a identidade visual do site partelli.pro.

PERÍODO
Cobrir as publicações desde a execução anterior (últimos 2 a 3 dias; na segunda-feira, cobrir desde sexta-feira).

FONTES E TEMAS (use WebSearch e WebFetch, sem tentar acessar redes sociais que exijam login; páginas bloqueadas por robots.txt não devem ser buscadas por outros meios)
1. Ministério da Saúde (gov.br/saude, listagem mensal em gov.br/saude/pt-br/assuntos/noticias-ms/AAAA/mes), Anvisa, Fiocruz, Instituto Butantan, OPAS/OMS (PAHO/WHO), CDC, SBIm, Canal Saúde.
2. Portarias, resoluções e normas novas do SUS (Diário Oficial da União, CIT, CNS, CONASS, CONASEMS; a legislação diária do portal.conasems.org.br é boa fonte).
3. Financiamento e captação de recursos: emendas parlamentares para saúde, habilitações, incentivos, editais e repasses fundo a fundo.
4. Indicadores e alertas epidemiológicos: vigilância (dengue, arboviroses, vacinação e coberturas, respiratórias), com dados e percentuais quando divulgados oficialmente.
5. Saúde digital e informática em saúde (e-SUS APS, RNDS, CNES, SISAB), incluindo inteligência artificial aplicada à saúde.
6. Atenção especial a Espírito Santo, Tocantins, Pará e Pernambuco quando houver notícia relevante.

ESTRUTURA DA NEWSLETTER (leitura dinâmica, escaneável em 3 a 5 minutos)
1. Barra superior azul escura com bandeira do Espírito Santo (3 faixas em células de tabela: #4C93D6, #FFFFFF, #F1A7BF), nome "Rafael Partelli" (link para https://partelli.pro) e data da edição. Abaixo, bloco hero azul escuro com o rótulo "Radar da gestão em saúde", título "Radar Saúde Pública", frase "Notícias oficiais selecionadas para quem planeja e decide a saúde pública.", credenciais "Administrador, Gestor de Saúde Pública, Auditor e Analista de Dados / CRA/ES 15721 · Membro da SBIS · Espírito Santo" e a foto https://partelli.pro/img/rafael-partelli.jpg (width 130, alt "Rafael Partelli", cantos superiores arredondados) à direita. Número da edição só se for possível inferir.
2. "Em 30 segundos": 3 a 4 frases curtas com o essencial do período, em bloco com fundo #F3F6FB e borda esquerda verde.
3. Destaque principal: a notícia de maior impacto, em card maior, com título (link), 2 a 3 linhas de resumo, dado ou percentual oficial quando houver, "Por que importa para a gestão" e botão verde "Ler matéria completa".
4. "Demais destaques" (até 7), em cards compactos com etiqueta em pílula (Normas e portarias, Financiamento, Epidemiologia, Saúde digital, Regional). Cada card: título (link), resumo de 1 a 2 linhas, fonte e data, e botão azul "Ler matéria" com a URL original.
5. "Indicadores em números": 4 blocos grandes (2 por linha) no estilo do site, com valor em destaque (32px, azul escuro), variação em percentual (verde se positivo) e descrição, mais linha de fontes. Somente dados publicados oficialmente.
6. "Oportunidades e riscos": dois blocos (verde e vermelho claro) que empilham no celular.
7. "Como superar e ampliar metas": 3 sugestões numeradas em círculos azuis.
8. "Próximo passo": caixa azul escura #0C326F com texto branco e uma ação clara.
9. Bloco de contato (fundo #F3F6FB): "Precisa de apoio em planejamento, indicadores ou captação de recursos?", botão verde "Falar comigo" (https://partelli.pro/#contato) e botão contorno azul "Biblioteca do Gestor" (https://partelli.pro/biblioteca/).
10. Rodapé escuro #08234F: Rafael Partelli, "Administrador · Gestor de Saúde Pública · CRA/ES 15721 · Membro da SBIS", partelli.pro, rafael@partelli.pro, +55 28 98117-4651, LinkedIn (https://www.linkedin.com/in/rafael-partelli-103a7728), Instagram (https://www.instagram.com/rafaelpartelli), premissas adotadas, aviso de que os dados vêm de fontes públicas linkadas e a menção "Edição automática preparada por Claude para Rafael Partelli".

DESIGN E UX DO E-MAIL (usar o parâmetro htmlBody; seguir a identidade do site partelli.pro)
- Paleta do site: azul escuro #0C326F (topo, hero, títulos), azul #1351B4 (botões, bordas de card, links), verde #168821 (CTA principal, sinais positivos), fundo suave #F3F6FB, linhas #D5DDEA, texto #1F2933, texto secundário #4B5563, rodapé #08234F. Vermelho #D4321F só para risco; amarelo claro #FFF8E1 (texto #8A5A00) só para etiqueta de atenção.
- Cards: borda 1px #D5DDEA, borda superior 4px #1351B4, cantos 12px, padding 18 a 22px. Etiquetas em pílula (radius 99px, 11px, negrito, maiúsculas): Normas em #E6EEFB/#1351B4, Financiamento em #E6F4E8/#168821, Regional em #EEF1F6/#0C326F, Saúde digital em #FFF8E1/#8A5A00, Destaque principal em #E6F4E8/#168821.
- Tipografia Arial/Helvetica; títulos de seção 22px negrito azul escuro #0C326F; corpo mínimo 15px; parágrafos curtos; bastante espaço entre blocos.
- HTML compatível com Gmail, Outlook e celular: layout em tabelas, CSS inline, largura máxima 640px, centralizado, fundo externo #F2F4F7 e miolo branco, sem JavaScript. A única imagem é a foto do site (com alt); tudo deve continuar legível se imagens forem bloqueadas.
- Botões bulletproof (link dentro de td com background-color, texto branco, padding, cantos arredondados 8px) e título de cada card também como link.
- Preheader oculto com a frase principal da edição.
- Enviar também a versão em texto simples no parâmetro body, com títulos, links e linha de contato.

REGRAS DE ESTILO E INTEGRIDADE
- Português do Brasil, tom claro, objetivo e estratégico, voltado à alta gestão.
- Não usar travessão (em dash ou en dash); usar vírgulas, parênteses ou dois pontos. Evitar jargões típicos de texto gerado por IA.
- Não inventar dados, números, normas ou links. Todo link deve ser uma URL real obtida na pesquisa e conferida. Se um item não tiver URL confirmada, não criar botão e indicar "fonte: nome do órgão". Se algo não for verificável, dizer que não foi confirmado. Se não houver novidade relevante em algum tema, dizer isso em uma linha.
- Priorizar notícias do período; não repetir itens já cobertos na edição anterior (edição de 01/10/2026: canetas emagrecedoras GLP-1 no SUS, Portaria 12.189 Melhor em Casa, UPAs do Pará, doação de sangue, liberação orçamentária de R$ 41,9 milhões, HU de Roraima, CAR-T no Ceará), salvo atualização relevante.

ENTREGA
Enviar por e-mail com mcp__Gmail__send_message, para rafael@partelli.pro (destinatário definido pelo Rafael em 01/10/2026; não enviar para outro endereço), com assunto: "Radar Saúde Pública | [destaque principal em até 8 palavras] | DD/MM/AAAA" (sem prefixo de teste). O corpo é a newsletter inteira em htmlBody (nunca apenas um resumo ou aviso). Se o envio falhar, informar o erro no resultado da execução.
```
