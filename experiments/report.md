# Relatório de experimentos

## Protocolo

- Desenvolvimento: 2000 textos, 10 classes.
- Teste OOD final: 210 textos; usado somente após a seleção do modelo e do limiar.
- Seleção: validação cruzada estratificada por grupo em 5 folds, GridSearchCV e F1-macro.
- Limiar de produção: 0,55, definido previamente no artigo. A varredura abaixo é apenas descritiva e usa a validação, não o OOD.
- Híbrido: inferência pelo Engine usado pelo CLI e pelo adaptador Telegram, não por uma implementação paralela.

## Comparação de modelos

| Modelo | CV F1-macro | OOD acurácia | OOD F1-macro | Melhor configuração |
|---|---:|---:|---:|---|
| MultinomialNB | 0.555 | 0.710 | 0.709 | `{'clf__estimator__alpha': 1.0}` |
| LinearSVC-Calibrated | 0.603 | 0.724 | 0.723 | `{'clf__estimator__C': 0.5}` |
| RandomForest-Calibrated | 0.568 | 0.648 | 0.658 | `{'clf__estimator__max_depth': None, 'clf__estimator__n_estimators': 80}` |

Modelo implantado: **LinearSVC-Calibrated**, selecionado somente pelo F1-macro de validação cruzada. O modelo foi reajustado em todo o corpus de desenvolvimento.

## Limiar de confiança na validação

| P mínimo | Acurácia | Fallback indevido em classe suportada | Fora de escopo aceito como suportado |
|---:|---:|---:|---:|
| 0.30 | 0.627 | 3.1% | 47.5% |
| 0.40 | 0.600 | 7.5% | 47.5% |
| 0.50 | 0.580 | 11.1% | 47.5% |
| 0.55 | 0.547 | 16.9% | 47.5% |
| 0.60 | 0.520 | 21.9% | 37.5% |
| 0.70 | 0.440 | 41.1% | 17.5% |

## Comparação ponta a ponta no OOD final

| Estratégia | Acurácia | F1-macro | Fallback indevido em classe suportada | Fora de escopo aceito como suportado |
|---|---:|---:|---:|---:|
| ML-only | 0.690 | 0.707 | 14.7% | 45.0% |
| Híbrido (Engine real) | 0.648 | 0.658 | 9.5% | 50.0% |

Neste conjunto OOD sintético, o híbrido teve acurácia inferior ao ML-only. Portanto, estes resultados não demonstram que as regras melhoram a classificação; o conjunto precisa ser ampliado e as regras devem ser reavaliadas.

O conjunto contém 200 frases OOD sintéticas e 10 casos específicos de regras, sem prefixos artificiais no texto de entrada.

A latência varia por máquina e execução; ela é impressa no terminal e gravada em `experiments/latest_run.json`, ignorado pelo Git, para não criar alterações ruidosas neste relatório.

## Desempenho por classe do híbrido

```text
                          precision    recall  f1-score   support

                   ajuda       0.73      0.52      0.61        21
   consultar_agendamento       0.67      0.40      0.50        20
      consultar_embarque       0.36      0.77      0.49        22
       consultar_estadia       0.87      0.65      0.74        20
   consultar_nota_fiscal       1.00      0.65      0.79        23
    consultar_ocorrencia       0.87      0.62      0.72        21
consultar_transportadora       0.85      0.55      0.67        20
 consultar_veiculo_patio       0.68      0.90      0.78        21
             fora_escopo       0.36      0.50      0.42        20
                saudacao       0.86      0.86      0.86        22

                accuracy                           0.65       210
               macro avg       0.72      0.64      0.66       210
            weighted avg       0.73      0.65      0.66       210

```

A classe fora de escopo deve ser interpretada com atenção: recall baixo indica mensagens não suportadas que passaram pelo limiar ou por regras. Os valores medem apenas este conjunto sintético e não representam conversas reais.

## Limitações

- O corpus OOD é provisório e sintético; precisa ser substituído ou ampliado com frases inéditas rotuladas independentemente.
- O limiar é fixado em 0,55; a varredura de validação não o altera após observar o teste OOD.
- Os resultados são específicos para as sementes, corpus e ambiente desta execução.