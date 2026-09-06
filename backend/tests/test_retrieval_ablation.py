from evals.run_retrieval_ablation import evaluate


def test_retrieval_ablation_reports_honest_comparable_variants() -> None:
    report = evaluate(k=5)
    assert report["cases"] >= 10
    assert set(report["results"]) == {"bm25", "hashing_baseline", "hybrid"}
    assert all(0 <= score <= 1 for score in report["results"].values())
    assert "not a trained embedding model" in report["dense_note"]
