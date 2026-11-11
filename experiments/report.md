# Relatorio de experimentos

Dados sintéticos: corpus OOD independente, com gírias, abreviações e ruído.

## Modelos e validação cruzada (5 folds, F1 macro)

| Modelo | CV F1 | OOD acurácia | OOD F1 macro | Melhor configuração |
|---|---:|---:|---:|---|
| MultinomialNB | 0.932 | 0.710 | 0.675 | `{'clf__estimator__alpha': 0.1}` |
| LinearSVC-Calibrated | 0.933 | 0.695 | 0.662 | `{'clf__estimator__C': 0.5}` |
| RandomForest-Calibrated | 0.934 | 0.538 | 0.519 | `{'clf__estimator__max_depth': None, 'clf__estimator__n_estimators': 80}` |

Modelo salvo: **LinearSVC-Calibrated**. Todos os candidatos usam calibração sigmoid. A escolha considera CV F1 e comportamento end-to-end no limiar; modelos com fallback excessivo foram penalizados.

## Comparação end-to-end OOD

- ML-ONLY: acurácia 0.695, F1 macro 0.708
- HYBRID (regras + ML + regex + limiar): acurácia 0.767, F1 macro 0.747

## Varredura de limiar

| P mínimo | accuracy | fallback in-scope | fallback out-of-scope |
|---:|---:|---:|---:|
| 0.30 | 0.714 | 11.1% | 70.0% |
| 0.40 | 0.714 | 14.7% | 70.0% |
| 0.50 | 0.710 | 17.9% | 50.0% |
| 0.55 | 0.695 | 22.1% | 25.0% |
| 0.60 | 0.681 | 26.3% | 25.0% |
| 0.70 | 0.576 | 41.6% | 25.0% |

## Efeito do limiar P < 0,55

- ML-ONLY fallback em entradas dentro do escopo: 22.1%; fora do escopo: 25.0%
- HYBRID fallback em entradas dentro do escopo: 15.3%; fora do escopo: 25.0%

## Latência real
- HYBRID: média 2.198 ms/mensagem; p95 4.268 ms/mensagem

## Relatório por classe
```text
                          precision    recall  f1-score   support

                   ajuda       0.44      0.76      0.56        21
   consultar_agendamento       1.00      0.50      0.67        20
      consultar_embarque       0.81      0.91      0.86        23
       consultar_estadia       0.45      1.00      0.62        20
   consultar_nota_fiscal       1.00      0.70      0.82        23
    consultar_ocorrencia       0.55      0.30      0.39        20
consultar_transportadora       0.80      1.00      0.89        20
 consultar_veiculo_patio       0.80      0.91      0.85        22
             fora_escopo       1.00      0.05      0.10        20
                saudacao       1.00      0.76      0.86        21

                accuracy                           0.70       210
               macro avg       0.79      0.69      0.66       210
            weighted avg       0.79      0.70      0.67       210

```