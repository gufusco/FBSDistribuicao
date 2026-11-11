from pathlib import Path
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from .preprocess import preprocess

def build_pipeline(kind="svc"):
    if kind == "nb":
        clf = CalibratedClassifierCV(MultinomialNB(), cv=3, method="sigmoid")
    elif kind == "rf":
        clf = CalibratedClassifierCV(RandomForestClassifier(random_state=42, n_jobs=-1), cv=3, method="sigmoid")
    else:
        clf = CalibratedClassifierCV(LinearSVC(), cv=3, method="sigmoid")
    return Pipeline([("tfidf", TfidfVectorizer(preprocessor=preprocess, ngram_range=(1,2))), ("clf", clf)])

def train_model(texts, labels, path):
    model = build_pipeline().fit(texts, labels)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return model

def load_model(path):
    return joblib.load(path)

def predict(model, text):
    probs = model.predict_proba([text])[0]
    idx = probs.argmax()
    return model.classes_[idx], float(probs[idx])
