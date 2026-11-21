import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from .preprocess import preprocess


def build_pipeline(kind="svc"):
    if kind == "nb":
        clf = CalibratedClassifierCV(MultinomialNB(), cv=3, method="sigmoid")
    elif kind == "rf":
        clf = CalibratedClassifierCV(
            RandomForestClassifier(random_state=42, n_jobs=-1), cv=3, method="sigmoid"
        )
    else:
        clf = CalibratedClassifierCV(LinearSVC(), cv=3, method="sigmoid")
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(preprocessor=preprocess, ngram_range=(1, 2))),
            ("clf", clf),
        ]
    )


def load_model(path):
    return joblib.load(path)


def predict(model, text):
    probs = model.predict_proba([text])[0]
    idx = probs.argmax()
    return model.classes_[idx], float(probs[idx])
