-- 1. Panorama nacional por ano
SELECT ano,
       SUM(internacoes)                                  AS internacoes,
       SUM(amputacoes)                                   AS amputacoes,
       SUM(obitos)                                       AS obitos,
       ROUND(SUM(val_total), 2)                          AS gasto_total,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2) AS pct_amputacao,
       ROUND(100.0 * SUM(obitos)     / SUM(internacoes), 2) AS letalidade
FROM gold
GROUP BY ano
ORDER BY ano;

-- 2. Taxa bruta por regiao e ano, por 100 mil habitantes
SELECT regiao, ano,
       SUM(internacoes)                                          AS internacoes,
       SUM(populacao)                                            AS populacao,
       ROUND(100000.0 * SUM(internacoes) / SUM(populacao), 1)    AS taxa_bruta
FROM gold
GROUP BY regiao, ano
ORDER BY regiao, ano;

-- 3. Efeito da pandemia: 2019 contra 2020-21 contra 2022-24
SELECT regiao,
       CASE WHEN ano = 2019 THEN '2019'
            WHEN ano IN (2020, 2021) THEN '2020-21'
            ELSE '2022-24' END                                   AS bloco,
       ROUND(100000.0 * SUM(internacoes) / SUM(populacao), 1)    AS taxa_bruta,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2)      AS pct_amputacao
FROM gold
GROUP BY regiao, bloco
ORDER BY regiao, bloco;

-- 4. Recorte de genero por regiao
SELECT regiao, sexo,
       SUM(internacoes)                                          AS internacoes,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2)      AS pct_amputacao,
       ROUND(100.0 * SUM(obitos)     / SUM(internacoes), 2)      AS letalidade
FROM gold
GROUP BY regiao, sexo
ORDER BY regiao, sexo;

-- 5. Municipios com mais amputacoes, respeitando o criterio principal do
--    ranking do ICVD: 20 internacoes somando 2019-2024 (docs/03-modelagem.md 3.5).
--    O ranking do ICVD acrescenta um segundo criterio (5 internacoes em cada
--    periodo) que esta consulta, exploratoria e sobre o periodo inteiro, nao aplica.
SELECT cod_municipio, uf, regiao,
       SUM(internacoes) AS internacoes,
       SUM(amputacoes)  AS amputacoes,
       ROUND(100.0 * SUM(amputacoes) / SUM(internacoes), 2) AS pct_amputacao
FROM gold
GROUP BY cod_municipio, uf, regiao
HAVING SUM(internacoes) >= 20
ORDER BY pct_amputacao DESC
LIMIT 50;
