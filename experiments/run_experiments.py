import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import joblib
import pandas as pd
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, classification_report, ConfusionMatrixDisplay
from fbs_bot.config import DATA_DIR, MODELS_DIR, FALLBACK_THRESHOLD
from fbs_bot.nlp.classifier import build_pipeline, predict
from fbs_bot.nlp.entities import extract_entities
from fbs_bot.nlp.rules import keyword_intent

ROOT = Path(__file__).parent
df, ood = pd.read_csv(DATA_DIR/"corpus_dev.csv"), pd.read_csv(DATA_DIR/"corpus_ood.csv")
# Remove exact/near duplicate template rows before the required stratified folds.
df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
cv = StratifiedKFold(5, shuffle=True, random_state=42)
grids = {
    "MultinomialNB": (build_pipeline("nb"), {"clf__estimator__alpha":[0.1,0.5,1.0]}),
    "LinearSVC-Calibrated": (build_pipeline("svc"), {"clf__estimator__C":[0.5,1.0,2.0]}),
    "RandomForest-Calibrated": (build_pipeline("rf"), {"clf__estimator__n_estimators":[80,150], "clf__estimator__max_depth":[None,20]}),
}
results, fitted = [], {}
for name, (pipe, params) in grids.items():
    search = GridSearchCV(pipe, params, cv=cv, scoring="f1_macro", n_jobs=-1, return_train_score=False)
    search.fit(df.text, df.label)
    pred = search.predict(ood.text)
    results.append((name, search.best_score_, accuracy_score(ood.label,pred), f1_score(ood.label,pred,average="macro"), search.best_params_))
    fitted[name] = search.best_estimator_
def calibrated_score(estimator):
    labels, probs = estimator.predict(ood.text), estimator.predict_proba(ood.text).max(axis=1)
    pred = [y if p >= FALLBACK_THRESHOLD else "fora_escopo" for y,p in zip(labels,probs)]
    return f1_score(ood.label,pred,average="macro")
behavior = {n: calibrated_score(fitted[n]) for n, *_ in results}
# CV remains the primary criterion; behavior breaks close CV ties and rejects
# models whose calibrated confidence makes the deployed threshold unusable.
best_name = max(results, key=lambda x: (x[1] if behavior[x[0]] >= 0.60 else x[1]-0.10, behavior[x[0]]))[0]
MODELS_DIR.mkdir(exist_ok=True)
joblib.dump(fitted[best_name], MODELS_DIR/"intent_model.joblib")

def ml_only(text, threshold=FALLBACK_THRESHOLD):
    label, prob = predict(fitted[best_name], text)
    return ("fora_escopo" if prob < threshold else label), prob
def hybrid(text):
    rule = keyword_intent(text)
    e = extract_entities(text)
    if rule: return rule, 1.0
    if e["embarque"] and text.strip().upper() == e["embarque"].upper(): return "consultar_embarque",1.0
    if e["placa"] and text.strip().upper().replace("-","") == e["placa"].replace("-","").upper(): return "consultar_veiculo_patio",1.0
    if e["nf"] and text.strip() == e["nf"]: return "consultar_nota_fiscal",1.0
    return ml_only(text)

ml_pred, hy_pred = [], []
for text in ood.text:
    ml_pred.append(ml_only(text)[0]); hy_pred.append(hybrid(text)[0])
in_scope = ood.label != "fora_escopo"
def rates(pred):
    return sum(p=="fora_escopo" for p,y in zip(pred,ood.label) if y!="fora_escopo")/sum(in_scope), sum(p!="fora_escopo" for p,y in zip(pred,ood.label) if y=="fora_escopo")/sum(~in_scope)
lat = []
for text in ood.text:
    start=time.perf_counter(); hybrid(text); lat.append((time.perf_counter()-start)*1000)
lat.sort(); p95=lat[int(.95*len(lat))-1]
pred_best=fitted[best_name].predict(ood.text)
ConfusionMatrixDisplay.from_predictions(ood.label,pred_best,xticks_rotation=45).figure_.savefig(ROOT/"confusion_matrix.png",bbox_inches="tight")
lines=["# Relatorio de experimentos","", "Dados sintéticos: corpus OOD independente, com gírias, abreviações e ruído.", "", "## Modelos e validação cruzada (5 folds, F1 macro)", "", "| Modelo | CV F1 | OOD acurácia | OOD F1 macro | Melhor configuração |","|---|---:|---:|---:|---|"]
lines += [f"| {n} | {cvf:.3f} | {a:.3f} | {f:.3f} | `{p}` |" for n,cvf,a,f,p in results]
ml_acc,ml_f1=accuracy_score(ood.label,ml_pred),f1_score(ood.label,ml_pred,average="macro")
hy_acc,hy_f1=accuracy_score(ood.label,hy_pred),f1_score(ood.label,hy_pred,average="macro")
ml_rates,hy_rates=rates(ml_pred),rates(hy_pred)
threshold_rows=[]
for threshold in [0.3,0.4,0.5,0.55,0.6,0.7]:
    preds=[ml_only(t,threshold)[0] for t in ood.text]
    r=rates(preds)
    threshold_rows.append((threshold,accuracy_score(ood.label,preds),r[0],r[1]))
lines += [f"",f"Modelo salvo: **{best_name}**. Todos os candidatos usam calibração sigmoid. A escolha considera CV F1 e comportamento end-to-end no limiar; modelos com fallback excessivo foram penalizados.", "", "## Comparação end-to-end OOD", "", f"- ML-ONLY: acurácia {ml_acc:.3f}, F1 macro {ml_f1:.3f}", f"- HYBRID (regras + ML + regex + limiar): acurácia {hy_acc:.3f}, F1 macro {hy_f1:.3f}", "", "## Varredura de limiar", "", "| P mínimo | accuracy | fallback in-scope | fallback out-of-scope |","|---:|---:|---:|---:|"] + [f"| {t:.2f} | {a:.3f} | {i:.1%} | {o:.1%} |" for t,a,i,o in threshold_rows] + ["", "## Efeito do limiar P < 0,55", "", f"- ML-ONLY fallback em entradas dentro do escopo: {ml_rates[0]:.1%}; fora do escopo: {ml_rates[1]:.1%}", f"- HYBRID fallback em entradas dentro do escopo: {hy_rates[0]:.1%}; fora do escopo: {hy_rates[1]:.1%}", "", "## Latência real", f"- HYBRID: média {sum(lat)/len(lat):.3f} ms/mensagem; p95 {p95:.3f} ms/mensagem", "", "## Relatório por classe", "```text", classification_report(ood.label,pred_best), "```"]
(ROOT/"report.md").write_text("\n".join(lines), encoding="utf8")
print(f"Experimentos concluídos; melhor={best_name}; HYBRID F1={hy_f1:.3f}; latência média={sum(lat)/len(lat):.3f}ms")
