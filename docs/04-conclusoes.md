# Conclusões

Análise de **804.249 internações por diabetes** no SUS entre 2019 e 2024, cobrindo os 5.570 municípios brasileiros. Todos os números abaixo vêm da execução real do pipeline descrito em [03-modelagem.md](03-modelagem.md).

**Validação prévia.** Antes de qualquer conclusão, os totais foram reconciliados contra o TabNet do DATASUS (cubo por local de residência, Lista de Morbidade CID-10 "Diabetes mellitus"): 162 combinações UF × ano comparadas, **erro relativo máximo de 0,000000% e divergência absoluta zero**. O filtro, a exclusão de AIHs de continuação e a agregação reproduzem exatamente os números oficiais.

---

## O que os dados mostram

### 1. As amputações cresceram doze vezes mais rápido que as internações

Entre 2019 e 2024, as internações por diabetes subiram 2,4% — de 136.276 para 139.598. As amputações de membro inferior subiram **29,2%**, de 9.215 para 11.904.

A proporção de internações que terminam em amputação passou de 6,76% para 8,53%. Não é que mais gente esteja adoecendo: é que quem chega ao hospital chega em estado pior. Amputação é o desfecho que marca o cuidado que faltou antes, e ele está ficando mais comum a cada ano.

No período inteiro foram **63.863 amputações** de membro inferior por diabetes.

### 2. A pandemia interrompeu o cuidado, e a conta veio em amputações

O recorte em três blocos mostra o mecanismo com clareza:

| | Internações/ano | Amputações/ano | % com amputação | Letalidade |
|---|---|---|---|---|
| 2019 (pré) | 136.276 | 9.215 | 6,76% | 4,22% |
| 2020–21 (choque) | 126.367 | 10.200 | **8,07%** | **4,71%** |
| 2022–24 (pós) | 138.413 | 11.416 | **8,25%** | 3,99% |

Durante a pandemia as internações **caíram 7,3%** — o hospital ficou menos acessível, consultas foram adiadas, o acompanhamento do doente crônico parou. No mesmo período as amputações **subiram 10,7%**. Menos gente internando, mais gente perdendo o pé.

### 3. O volume voltou; a gravidade não

Depois de 2022 o número de internações se recuperou e ultrapassou o patamar pré-pandemia. Mas a proporção que termina em amputação continuou subindo — **8,25%, pior que durante o próprio choque**. A letalidade caiu abaixo do nível de 2019, o que sugere que o hospital está salvando mais vidas; só que está salvando pessoas que chegam com a doença mais avançada.

O sistema recuperou a capacidade de internar. Não recuperou a capacidade de evitar que a internação fosse necessária.

### 4. A desigualdade regional é de duas vezes, e está aumentando

Taxa de internação padronizada por idade, por 100 mil habitantes:

| Região | 2019 | 2023–24 | Variação |
|---|---|---|---|
| Norte | 109,0 | **120,2** | **+10,3%** |
| Nordeste | 84,4 | 81,8 | −3,1% |
| Centro-Oeste | 62,7 | 65,0 | +3,7% |
| Sul | 64,2 | 60,7 | −5,5% |
| Sudeste | 54,4 | 58,3 | +7,2% |

O Norte interna **2,1 vezes mais** que o Sudeste, com a comparação já corrigida pela estrutura etária — ou seja, a diferença não é explicada por uma região ter mais idosos que a outra. E o Norte foi a região que mais piorou.

### 5. O paradoxo do Sudeste

O Sudeste tem a **menor** taxa de internação (58,3) e a **maior** proporção de amputação (9,82%). Os dois fatos juntos sugerem um sistema que filtra melhor: o caso leve é resolvido fora do hospital, e quem interna é o caso grave. Não é necessariamente cuidado pior — é uma população internada diferente.

Isso é um alerta metodológico embutido: taxa de internação sozinha não mede qualidade. É exatamente por isso que o índice combina três componentes em vez de olhar só um.

### 6. Homens são amputados 73% mais que mulheres, em todas as regiões

A hipótese de gênero se confirma, e de forma consistente:

| | Mulheres | Homens | Razão |
|---|---|---|---|
| Internações (2023–24) | 131.072 | 146.842 | 1,12 |
| % com amputação | 6,05% | **10,46%** | **1,73** |
| Letalidade | 4,18% | 3,50% | 0,84 |
| Idade média na internação | 54,6 | 56,3 | 1,03 |

A razão de amputação favorece as mulheres em **todas as cinco regiões**, variando de 1,51 (Norte) a 2,28 (Sul). Não é efeito de uma região puxando a média.

O detalhe que fecha o raciocínio: homens amputam muito mais, mas **morrem menos** no hospital, e chegam praticamente com a mesma idade. Isso não descreve uma população mais doente — descreve uma população que chega mais tarde, com a doença já em estágio cirúrgico. Pé diabético não vira amputação da noite para o dia; ele passa por meses de ferida que alguém poderia ter examinado.

### 7. Mais cobertura de atenção primária não apareceu associada a menos internação

A correlação entre cobertura de APS e taxa de internação é **positiva**: Spearman +0,237 em 2019 e +0,249 em 2023–24, ambas com p < 10⁻⁴³ (n = 3.365 municípios).

Isso contraria a expectativa que motivou o projeto. Três leituras possíveis, nenhuma verificável com estes dados:

- **Efeito de detecção.** Onde a atenção primária funciona, mais gente é diagnosticada e encaminhada. Mais cobertura produz mais internação registrada, não menos doença.
- **Causalidade reversa.** Municípios com mais carga de doença recebem mais investimento em APS.
- **Falácia ecológica.** A correlação é entre municípios, não entre pessoas. Municípios pequenos têm cobertura próxima de 100% por construção e perfis epidemiológicos distintos.

O achado honesto é que **este desenho não sustenta a afirmação de que ampliar a APS reduz internação por diabetes**. Sustentar isso exigiria dado individual e controle de confundidores.

### 8. Não houve recuperação geral — houve recuperação desigual

Dos 3.365 municípios no ranking, **1.679 pioraram e 1.686 melhoraram** entre 2019 e 2023–24. É praticamente um empate, e é justamente esse o ponto: não existe uma trajetória nacional única.

Por região, a média da variação do ICVD:

| Região | Variação média | Municípios |
|---|---|---|
| Centro-Oeste | **+0,0127** | 240 |
| Nordeste | +0,0069 | 1.179 |
| Norte | −0,0101 | 296 |
| Sul | −0,0112 | 647 |
| Sudeste | −0,0124 | 1.003 |

Centro-Oeste e Nordeste pioraram; Norte, Sul e Sudeste melhoraram. O Norte melhorou no índice composto apesar de ter a pior taxa de internação — porque reduziu a proporção de amputação (6,79% para 5,96%, a única região que caiu).

### 9. O custo

**R$ 759.276.942** pagos pelo SUS em internações por diabetes no período, e **5.304.606 dias** de leito ocupados. O gasto anual subiu 42% entre 2019 e 2024, mais rápido que o número de internações — coerente com casos mais graves e procedimentos mais caros.

---

## Municípios prioritários

Os dez piores ICVD em 2023–24, entre os 3.365 que passaram nos critérios de elegibilidade:

| Município | UF | População | ICVD 2023–24 | Variação |
|---|---|---|---|---|
| Jandaia | GO | 6.272 | 0,639 | +0,574 |
| Cabaceiras do Paraguaçu | BA | 16.559 | 0,610 | +0,296 |
| Forquilha | CE | 24.173 | 0,588 | +0,157 |
| Taquarana | AL | 19.032 | 0,568 | +0,216 |
| Icapuí | CE | 21.433 | 0,559 | +0,448 |
| Terenos | MS | 17.652 | 0,550 | −0,041 |
| Aveiro | PA | 18.290 | 0,545 | +0,178 |
| Maraial | PE | 9.359 | 0,542 | +0,505 |
| Lebon Régis | SC | 11.472 | 0,538 | +0,426 |

Chama atenção que **todos são municípios pequenos**, de 6 a 24 mil habitantes, mesmo depois do corte de 20 internações. Isso é uma limitação real do índice, discutida abaixo, e a lista deve ser lida como ponto de partida para investigação local — não como veredicto.

---

## Recomendações

**Rastreamento de pé diabético dirigido a homens.** É a recomendação com a base empírica mais sólida deste trabalho: 1,73 vez mais amputações, consistente nas cinco regiões, com idade de internação equivalente e letalidade menor. O ponto de intervenção é o exame periódico dos pés na atenção primária, e o público que não está chegando a ele é masculino.

**Priorizar o Norte pela taxa, o Sudeste pela gravidade.** São problemas diferentes e pedem respostas diferentes. O Norte interna duas vezes mais e piorou 10,3% — é problema de acesso e prevenção. O Sudeste interna pouco mas amputa muito — é problema de quem chega tarde apesar de haver rede.

**Tratar a proporção de amputação como indicador de monitoramento contínuo.** Ela subiu em quatro das cinco regiões e cresceu doze vezes mais rápido que o volume de internações. É o indicador que enxerga a deterioração antes de ela aparecer na contagem de internações.

**Investigar os municípios que mais pioraram.** Jandaia (GO), Maraial (PE) e Icapuí (CE) saíram de um ICVD próximo de zero em 2019 para acima de 0,44 em 2023–24. Uma mudança dessa magnitude em municípios pequenos costuma ter causa local identificável — fechamento de serviço, perda de equipe, mudança de referência hospitalar.

---

## Limitações

**O ranking do top-100 não é robusto à repesagem.** A análise de sensibilidade recalculou o ICVD sob três esquemas alternativos de peso. A correlação de Spearman ficou entre 0,939 e 0,959, acima do critério de 0,9 — a ordenação geral é estável. Mas a sobreposição do top-100 variou muito: 83% no esquema "desfecho", 77% em "gravidade" e apenas **29% em "acesso"** (metade do peso na taxa de internação). Isso reprova o critério de 80% que eu mesmo estabeleci, e a leitura correta é: os três componentes medem coisas genuinamente distintas, e a identidade dos cem piores depende de qual delas se privilegia. O ICVD serve para ordenar e comparar; não serve para cravar uma lista definitiva de piores.

**Os extremos do ranking são dominados por municípios pequenos.** Mesmo com o corte de 20 internações e o piso de 5 por período, os dez piores têm entre 6 e 24 mil habitantes. O corte reduz o ruído, não o elimina.

**O filtro simples subestima amputações.** Só entram internações com diabetes como diagnóstico principal. Quando o pé diabético interna com a infecção codificada como principal, a internação fica de fora. O viés é aproximadamente uniforme entre municípios, então a comparação se sustenta, mas o total absoluto de 63.863 amputações é um piso, não o número real.

**Práticas de codificação variam entre regiões.** Como o objeto do estudo é justamente a comparação regional, essa variação é uma fonte de viés que os dados administrativos não permitem medir.

**A cobertura de APS tem quebra metodológica.** As duas séries disponíveis não se sobrepõem em nenhum mês e a média salta 42,2 pontos na virada de 2020 para 2021. Por isso ela ficou fora do índice e só aparece como contexto, sempre dentro de um único período.

**Correlação não é causalidade.** Todas as associações aqui são ecológicas, entre municípios. Nenhuma sustenta afirmação sobre indivíduos.

**O IDHM disponível é de 2010.** Foi usado apenas como contexto na discussão, nunca como componente do índice.
