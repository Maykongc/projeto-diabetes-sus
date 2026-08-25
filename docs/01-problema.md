# O problema

## Pergunta central

O SUS entrega o mesmo cuidado ao diabético em todo o território brasileiro? E, onde não entrega, quem paga a conta?

O diabetes é uma doença crônica cuja gravidade não está na doença em si, mas nas complicações que surgem quando o acompanhamento falha: pé diabético que evolui para amputação, insuficiência renal, cegueira, internação por descompensação metabólica aguda. Essas complicações são majoritariamente evitáveis com atenção primária adequada — consultas regulares, controle glicêmico, exame de pé em quem já tem a doença. Uma internação por complicação de diabetes não é, portanto, um evento aleatório: é o registro de uma falha assistencial que aconteceu antes, em algum ponto entre o diagnóstico e a descompensação.

Este projeto usa dados administrativos do SUS para medir essa falha em nível municipal, ano a ano, entre 2019 e 2024, e para verificar se ela se distribui de forma homogênea pelo país ou se concentra em regiões e municípios específicos.

## Por que este problema é adequado à análise de dados

Três características tornam o diabetes, e especificamente as internações evitáveis por diabetes, um objeto tratável por dados administrativos públicos, e não apenas por pesquisa de campo:

A falha é mensurável. Cada internação por diabetes gera uma Autorização de Internação Hospitalar (AIH), registrada no Sistema de Informações Hospitalares do SUS (SIH/SUS), com município de residência do paciente, diagnóstico principal codificado em CID-10, procedimento realizado, valor pago, tempo de permanência, desfecho (alta ou óbito), idade e sexo. Não é preciso entrevistar ninguém: o sistema de saúde já produz o registro como subproduto do próprio atendimento.

A causa provável também é observável. A cobertura de Atenção Primária à Saúde e da Estratégia Saúde da Família — a linha de frente que deveria evitar a descompensação antes que ela vire internação — é publicada mensalmente pelo Ministério da Saúde, por município, no e-Gestor Atenção Básica. Isso permite não só constatar a desigualdade no desfecho, mas relacioná-la a uma causa estrutural mensurável, em vez de tratá-la como um fato isolado.

A desigualdade é hipótese, não conclusão. Se o cuidado fosse homogêneo pelo território, a taxa de internação evitável por diabetes, ajustada pela composição etária de cada município, seria semelhante entre eles. O trabalho aqui não presume a desigualdade: ele a testa, calculando essa taxa padronizada para os 5.570 municípios brasileiros e verificando o quanto ela varia.

## Relevância social

O Brasil está entre os países com maior número absoluto de pessoas com diabetes no mundo, e a doença é hoje a principal causa de amputação não traumática de membro inferior no país. Cada amputação representa custo hospitalar direto, perda de capacidade produtiva, provável concessão de benefício previdenciário, e — para a pessoa que a sofre — um desfecho irreversível que nenhuma política pública reverte depois do fato.

Um mapa que identifique onde essas internações e amputações se concentram, controlando pelo perfil etário local para que a comparação entre um município jovem e um envelhecido seja justa, é insumo direto para priorização orçamentária em saúde: mostra onde reforçar atenção primária tem maior potencial de evitar dano grave, em vez de distribuir recursos de forma uniforme sobre um problema que não é uniforme.

## Eixo analítico: choque e recuperação desigual

A janela escolhida, 2019 a 2024, não é arbitrária. Ela contém um ano de referência anterior à pandemia (2019), dois anos de forte distorção assistencial (2020 e 2021) e três anos de recuperação (2022 a 2024). A pandemia de covid-19 interrompeu, em graus variados, o acompanhamento do doente crônico em todo o país — consultas de rotina foram adiadas, unidades básicas de saúde foram realocadas para o enfrentamento emergencial, pacientes evitaram procurar atendimento por medo de exposição ao vírus.

A hipótese que organiza a análise é que essa interrupção não teve o mesmo efeito em todo lugar: onde a atenção primária já era frágil antes de 2020, a interrupção teve mais chance de se converter em desfechos graves — mais internações por descompensação, mais amputações, mais óbitos hospitalares. E que a recuperação posterior, entre 2022 e 2024, também não foi uniforme: alguns municípios voltaram ao patamar pré-pandêmico ou melhoraram, outros não.

Para testar essa hipótese, o projeto compara dois momentos — a linha de base de 2019 e a situação mais recente disponível, a média de 2023–2024 — sob um índice composto de vulnerabilidade construído para ser comparável entre os dois períodos (ver `03-modelagem.md`). A diferença entre eles, calculada município a município, é o indicador central do eixo "choque e recuperação desigual": positiva, indica piora; negativa, indica recuperação. Esse indicador ainda depende da execução do pipeline de dados e por isso não aparece com valores neste documento — a estrutura da análise está pronta, os números estão pendentes (ver `00-execucao-manual.md` e `04-conclusoes.md`).
