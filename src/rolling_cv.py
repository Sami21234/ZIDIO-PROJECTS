import pandas as pd
from src.model import prepare_model_data, train_model, predict, wape


def rolling_origin_cv(features_df: pd.DataFrame, n_folds: int = 4, n_test_weeks: int = 8, min_train_weeks: int = 20):
    """
    Rolling-origin backtest: repeatedly train on the past, test on the next
    n_test_weeks, moving the cutoff backward through history for each fold.
    NEVER a random split - that would leak the future into training.
    """
    model_df = prepare_model_data(features_df)
    all_weeks = sorted(model_df["week"].unique())
    last_idx = len(all_weeks) - 1
    results = []

    for fold in range(n_folds):
        test_end_idx = last_idx - fold * n_test_weeks
        test_start_idx = test_end_idx - n_test_weeks + 1
        if test_start_idx < min_train_weeks:
            break
        train_end_idx = test_start_idx - 1

        train_weeks = all_weeks[:train_end_idx + 1]
        test_weeks = all_weeks[test_start_idx:test_end_idx + 1]

        train = model_df[model_df["week"].isin(train_weeks)]
        test = model_df[model_df["week"].isin(test_weeks)]
        if len(train) == 0 or len(test) == 0:
            continue

        model = train_model(train)
        preds = predict(model, test)

        model_wape = wape(test["target"], preds)
        baseline_wape = wape(test["target"], test["lag_52"].fillna(test["roll_mean_4"]))

        results.append({
            "fold": fold, "test_start": test_weeks[0], "test_end": test_weeks[-1],
            "model_wape": model_wape, "baseline_wape": baseline_wape,
        })
        print(f"Fold {fold}: test={test_weeks[0].date()}..{test_weeks[-1].date()} "
              f"| model WAPE={model_wape:.3f} | baseline WAPE={baseline_wape:.3f}")

    return pd.DataFrame(results)


if __name__ == "__main__":
    features = pd.read_csv("data/processed/features.csv", parse_dates=["week"], dtype={"sku_id": str})
    results = rolling_origin_cv(features)
    print(f"\nAverage model WAPE:    {results['model_wape'].mean():.3f}")
    print(f"Average baseline WAPE: {results['baseline_wape'].mean():.3f}")
    improvement = (1 - results['model_wape'].mean() / results['baseline_wape'].mean()) * 100
    print(f"Improvement over baseline: {improvement:.1f}%")