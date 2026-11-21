import json
import sys
import tempfile
import time
from pathlib import Path

import joblib
import matplotlib
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    f1_score,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "experiments"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from seed_db import seed_database

from fbs_bot.config import (
    DATA_DIR,
    FALLBACK_THRESHOLD,
    MODEL_PATH,
)
from fbs_bot.engine import Engine
from fbs_bot.nlp.classifier import predict
from fbs_bot.nlp.training import select_model

THRESHOLDS = (0.30, 0.40, 0.50, 0.55, 0.60, 0.70)


def apply_threshold(model, texts, threshold):
    predictions = []
    probabilities = []
    for text in texts:
        label, probability = predict(model, text)
        probabilities.append(probability)
        predictions.append(label if probability >= threshold else "fora_escopo")
    return predictions, probabilities


def fallback_rates(predictions, labels):
    in_scope = [label != "fora_escopo" for label in labels]
    out_scope_count = sum(not value for value in in_scope)
    in_scope_count = sum(in_scope)
    false_fallback = sum(
        prediction == "fora_escopo" and included
        for prediction, included in zip(predictions, in_scope)
    )
    missed_out_scope = sum(
        prediction != "fora_escopo" and not included
        for prediction, included in zip(predictions, in_scope)
    )
    return (
        false_fallback / in_scope_count if in_scope_count else 0.0,
        missed_out_scope / out_scope_count if out_scope_count else 0.0,
    )


def evaluate_hybrid(texts, model_path, data_dir):
    engine = Engine(model_path=model_path, data_dir=data_dir)
    predictions = []
    durations_ms = []
    try:
        for text in texts:
            engine.context.clear()
            started = time.perf_counter()
            engine.handle_message(1, text)
            durations_ms.append((time.perf_counter() - started) * 1000)
            intent = engine.conn.execute(
                """
                SELECT intent FROM auditoria
                WHERE chat_id=1
                ORDER BY rowid DESC
                LIMIT 1
                """
            ).fetchone()
            predictions.append(intent["intent"])
    finally:
        engine.conn.close()
    return predictions, durations_ms


def main():
    development = pd.read_csv(DATA_DIR / "corpus_dev.csv")
    ood = pd.read_csv(DATA_DIR / "corpus_ood.csv")
    if "kind" not in ood:
        ood["kind"] = "ood"

    selection = select_model(development)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(selection.best_model, MODEL_PATH)

    result_rows = []
    for result in selection.results:
        predictions = result["final_model"].predict(ood["text"])
        result_rows.append(
            {
                "name": result["name"],
                "cv_f1_macro": result["cv_f1_macro"],
                "ood_accuracy": accuracy_score(ood["label"], predictions),
                "ood_f1_macro": f1_score(ood["label"], predictions, average="macro"),
                "best_params": result["best_params"],
            }
        )

    validation = selection.validation_data
    validation_labels = selection.validation_model.predict(validation["text"])
    validation_probabilities = selection.validation_model.predict_proba(
        validation["text"]
    ).max(axis=1)
    validation_sweep = []
    for threshold in THRESHOLDS:
        predictions = [
            label if probability >= threshold else "fora_escopo"
            for label, probability in zip(validation_labels, validation_probabilities)
        ]
        in_fallback, out_missed = fallback_rates(predictions, validation["label"])
        validation_sweep.append(
            {
                "threshold": threshold,
                "accuracy": accuracy_score(validation["label"], predictions),
                "in_scope_fallback": in_fallback,
                "out_scope_missed": out_missed,
            }
        )

    ml_predictions, _ = apply_threshold(
        selection.best_model,
        ood["text"],
        FALLBACK_THRESHOLD,
    )
    with tempfile.TemporaryDirectory(prefix="fbs-experiment-") as directory:
        experiment_data = Path(directory) / "data"
        seed_database(experiment_data)
        hybrid_predictions, durations_ms = evaluate_hybrid(
            ood["text"], MODEL_PATH, experiment_data
        )
    measured = sorted(durations_ms)
    latency = {
        "mean_ms": sum(measured) / len(measured),
        "p95_ms": measured[min(int(0.95 * len(measured)), len(measured) - 1)],
        "sample_count": len(measured),
    }

    ml_in_fallback, ml_out_missed = fallback_rates(ml_predictions, ood["label"])
    hybrid_in_fallback, hybrid_out_missed = fallback_rates(
        hybrid_predictions, ood["label"]
    )

    labels = sorted(set(ood["label"]) | {"fora_escopo"})
    figure, axis = plt.subplots(figsize=(11, 9))
    ConfusionMatrixDisplay.from_predictions(
        ood["label"],
        hybrid_predictions,
        labels=labels,
        xticks_rotation=45,
        ax=axis,
    )
    figure.savefig(OUTPUT_DIR / "confusion_matrix.png", bbox_inches="tight")
    plt.close(figure)

    lines = [
        "# Relatório de experimentos",
        "",
        "## Protocolo",
        "",
        (
            f"- Desenvolvimento: {len(development)} textos, "
            f"{development['label'].nunique()} classes."
        ),
        (
            f"- Teste OOD final: {len(ood)} textos; "
            "usado somente após a seleção do modelo e do limiar."
        ),
        (
            "- Seleção: validação cruzada estratificada por grupo em 5 folds, "
            "GridSearchCV e F1-macro."
        ),
        (
            "- Limiar de produção: 0,55, definido previamente no artigo. "
            "A varredura abaixo é apenas descritiva e usa a validação, não o OOD."
        ),
        (
            "- Híbrido: inferência pelo Engine usado pelo CLI e pelo adaptador "
            "Telegram, não por uma implementação paralela."
        ),
        "",
        "## Comparação de modelos",
        "",
        "| Modelo | CV F1-macro | OOD acurácia | OOD F1-macro | Melhor configuração |",
        "|---|---:|---:|---:|---|",
    ]
    lines.extend(
        f"| {row['name']} | {row['cv_f1_macro']:.3f} | "
        f"{row['ood_accuracy']:.3f} | {row['ood_f1_macro']:.3f} | "
        f"`{row['best_params']}` |"
        for row in result_rows
    )
    lines.extend(
        [
            "",
            (
                f"Modelo implantado: **{selection.best_name}**, selecionado "
                "somente pelo F1-macro de validação cruzada. O modelo foi "
                "reajustado em todo o corpus de desenvolvimento."
            ),
            "",
            "## Limiar de confiança na validação",
            "",
            (
                "| P mínimo | Acurácia | Fallback indevido em classe suportada | "
                "Fora de escopo aceito como suportado |"
            ),
            "|---:|---:|---:|---:|",
        ]
    )
    lines.extend(
        f"| {row['threshold']:.2f} | {row['accuracy']:.3f} | "
        f"{row['in_scope_fallback']:.1%} | {row['out_scope_missed']:.1%} |"
        for row in validation_sweep
    )

    ml_accuracy = accuracy_score(ood["label"], ml_predictions)
    ml_f1 = f1_score(ood["label"], ml_predictions, average="macro")
    hybrid_accuracy = accuracy_score(ood["label"], hybrid_predictions)
    hybrid_f1 = f1_score(ood["label"], hybrid_predictions, average="macro")
    if hybrid_accuracy >= ml_accuracy:
        hybrid_interpretation = (
            "Neste conjunto OOD sintético, o híbrido teve acurácia igual ou "
            "superior ao ML-only. Isso é evidência preliminar, não uma "
            "garantia de melhoria em dados reais."
        )
    else:
        hybrid_interpretation = (
            "Neste conjunto OOD sintético, o híbrido teve acurácia inferior "
            "ao ML-only. Portanto, estes resultados não demonstram que as "
            "regras melhoram a classificação; o conjunto precisa ser ampliado "
            "e as regras devem ser reavaliadas."
        )
    lines.extend(
        [
            "",
            "## Comparação ponta a ponta no OOD final",
            "",
            (
                "| Estratégia | Acurácia | F1-macro | Fallback indevido em classe suportada | "
                "Fora de escopo aceito como suportado |"
            ),
            "|---|---:|---:|---:|---:|",
            (
                f"| ML-only | {ml_accuracy:.3f} | {ml_f1:.3f} | "
                f"{ml_in_fallback:.1%} | {ml_out_missed:.1%} |"
            ),
            (
                f"| Híbrido (Engine real) | {hybrid_accuracy:.3f} | "
                f"{hybrid_f1:.3f} | {hybrid_in_fallback:.1%} | "
                f"{hybrid_out_missed:.1%} |"
            ),
            "",
            hybrid_interpretation,
            "",
            (
                f"O conjunto contém {sum(ood['kind'] == 'ood')} frases OOD "
                f"sintéticas e {sum(ood['kind'] == 'regra')} casos específicos "
                "de regras, sem prefixos artificiais no texto de entrada."
            ),
            "",
            (
                "A latência varia por máquina e execução; ela é impressa no "
                "terminal e gravada em `experiments/latest_run.json`, ignorado "
                "pelo Git, para não criar alterações ruidosas neste relatório."
            ),
            "",
            "## Desempenho por classe do híbrido",
            "",
            "```text",
            classification_report(
                ood["label"],
                hybrid_predictions,
                labels=labels,
                zero_division=0,
            ),
            "```",
            "",
            (
                "A classe fora de escopo deve ser interpretada com atenção: "
                "recall baixo indica mensagens não suportadas que passaram "
                "pelo limiar ou por regras. Os valores medem apenas este "
                "conjunto sintético e não representam conversas reais."
            ),
            "",
            "## Limitações",
            "",
            (
                "- O corpus OOD é provisório e sintético; precisa ser substituído "
                "ou ampliado com frases inéditas rotuladas independentemente."
            ),
            (
                "- O limiar é fixado em 0,55; a varredura de validação não o "
                "altera após observar o teste OOD."
            ),
            (
                "- Os resultados são específicos para as sementes, corpus e "
                "ambiente desta execução."
            ),
        ]
    )
    (OUTPUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (OUTPUT_DIR / "latest_run.json").write_text(
        json.dumps(
            {
                "best_model": selection.best_name,
                "hybrid_accuracy": hybrid_accuracy,
                "hybrid_f1_macro": hybrid_f1,
                "latency": latency,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Modelo selecionado por CV: {selection.best_name}")
    print(
        f"ML-only OOD: accuracy={ml_accuracy:.3f}, F1-macro={ml_f1:.3f}; "
        f"Engine híbrido OOD: accuracy={hybrid_accuracy:.3f}, "
        f"F1-macro={hybrid_f1:.3f}"
    )
    print(
        f"Latência do Engine: média {latency['mean_ms']:.3f} ms, "
        f"p95 {latency['p95_ms']:.3f} ms ({latency['sample_count']} mensagens)"
    )
    print(f"Relatório salvo em {OUTPUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
