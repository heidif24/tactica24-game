import csv
from datetime import datetime, timedelta, timezone

from backend.calibration import calibrate_probability


def test_calibration_requires_timestamped_out_of_sample_data(tmp_path, monkeypatch):
    path = tmp_path / "history.csv"
    monkeypatch.setenv("T24_CALIBRATION_FILE", str(path))
    monkeypatch.setenv("T24_CALIBRATION_MIN_TOTAL", "200")
    monkeypatch.setenv("T24_CALIBRATION_MIN_BIN", "30")
    now = datetime.now(timezone.utc)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["market_category", "sub_market", "time_window", "model_version", "predicted_probability", "outcome", "predicted_at", "kickoff_at", "settled_at"])
        for i in range(220):
            predicted = now - timedelta(days=3)
            settled = now - timedelta(days=2)
            writer.writerow(["goals", "total_goals", "full_match", "tactica24-poisson-v2", "0.90", 1 if i < 190 else 0, predicted.isoformat(), (now - timedelta(days=2, hours=1)).isoformat(), settled.isoformat()])
    probability, count = calibrate_probability("goals", "total_goals", "full_match", 0.90)
    assert count == 220
    assert probability is not None
    assert 0 < probability < 0.90


def test_calibration_rejects_rows_predicted_after_settlement(tmp_path, monkeypatch):
    path = tmp_path / "history.csv"
    monkeypatch.setenv("T24_CALIBRATION_FILE", str(path))
    monkeypatch.setenv("T24_CALIBRATION_MIN_TOTAL", "1")
    monkeypatch.setenv("T24_CALIBRATION_MIN_BIN", "1")
    now = datetime.now(timezone.utc)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["market_category", "sub_market", "time_window", "predicted_probability", "outcome", "predicted_at", "settled_at"])
        writer.writerow(["goals", "total_goals", "full_match", "tactica24-poisson-v2", "0.90", 1, now.isoformat(), (now - timedelta(days=2)).isoformat(), (now - timedelta(days=1)).isoformat()])
    probability, count = calibrate_probability("goals", "total_goals", "full_match", 0.90)
    assert probability is None
    assert count == 0
