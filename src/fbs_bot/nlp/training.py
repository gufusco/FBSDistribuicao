from dataclasses import dataclass

import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold

from .classifier import build_pipeline

MODEL_GRIDS = {
    "MultinomialNB": (
        "nb",
        {"clf__estimator__alpha": [0.1, 0.5, 1.0]},
    ),
    "LinearSVC-Calibrated": (
        "svc",
        {"clf__estimator__C": [0.5, 1.0, 2.0]},
    ),
    "RandomForest-Calibrated": (
        "rf",
        {
            "clf__estimator__n_estimators": [80, 150],
            "clf__estimator__max_depth": [None, 20],
        },
    ),
}


@dataclass
class ModelSelection:
    best_name: str
    best_model: object
    validation_model: object
    validation_data: pd.DataFrame
    results: list


def select_model(data: pd.DataFrame) -> ModelSelection:
    required_columns = {"text", "label", "group"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise ValueError(
            "O corpus de desenvolvimento precisa das colunas "
            + ", ".join(sorted(required_columns))
            + "; ausentes: "
            + ", ".join(sorted(missing_columns))
        )
    if data["text"].duplicated().any():
        raise ValueError("O corpus contém textos duplicados.")
    if data.groupby("text")["label"].nunique().gt(1).any():
        raise ValueError("Há textos associados a mais de um rótulo.")

    outer_cv = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )
    train_indices, validation_indices = next(
        outer_cv.split(data["text"], data["label"], groups=data["group"])
    )
    training = data.iloc[train_indices].reset_index(drop=True)
    validation = data.iloc[validation_indices].reset_index(drop=True)
    inner_cv = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=43,
    )

    results = []
    for model_name, (model_kind, parameter_grid) in MODEL_GRIDS.items():
        search = GridSearchCV(
            build_pipeline(model_kind),
            parameter_grid,
            cv=inner_cv,
            scoring="f1_macro",
            n_jobs=-1,
            return_train_score=False,
            refit=True,
        )
        search.fit(
            training["text"],
            training["label"],
            groups=training["group"],
        )
        results.append(
            {
                "name": model_name,
                "cv_f1_macro": search.best_score_,
                "best_params": search.best_params_,
                "validation_model": search.best_estimator_,
                "final_model": clone(search.best_estimator_).fit(
                    data["text"], data["label"]
                ),
                "validation_accuracy": search.score(
                    validation["text"], validation["label"]
                ),
            }
        )

    selected = max(
        results,
        key=lambda result: (
            result["cv_f1_macro"],
            -list(MODEL_GRIDS).index(result["name"]),
        ),
    )
    validation_model = selected["validation_model"]
    return ModelSelection(
        best_name=selected["name"],
        best_model=selected["final_model"],
        validation_model=validation_model,
        validation_data=validation,
        results=results,
    )
