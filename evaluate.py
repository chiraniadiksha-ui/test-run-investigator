from datetime import datetime

from sentence_transformers import SentenceTransformer

from investigate import (
    PROJECT_DIR,
    read_run_log,
    build_search_query,
    retrieve_guides,
    load_investigation_model,
    generate_investigation,
)


def main():
    run_ids = ["RUN-1042"]

    # A new folder for each evaluation session preserves earlier reports.
    session_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir = PROJECT_DIR / "evaluation_results" / session_name
    output_dir.mkdir(parents=True, exist_ok=False)

    # Both models are loaded once, before processing the runs.
    print("\nLoading embedding model...")
    embedding_model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
    )

    loaded_model = load_investigation_model()

    for run_id in run_ids:
        print(f"\nEvaluating: {run_id}")

        log_text = read_run_log(run_id)
        query = build_search_query(log_text)

        guides = retrieve_guides(
            query,
            embedding_model,
            top_k=1,
        )

        report = generate_investigation(
            run_id=run_id,
            log_text=log_text,
            retrieved_guides=guides,
            loaded_model=loaded_model,
        )

        report_path = output_dir / f"{run_id}.md"
        report_path.write_text(
            f"# Investigation: {run_id}\n\n{report}\n",
            encoding="utf-8",
        )

        print(f"Saved report: {report_path}")

    print("\nReports saved for manual review.")
    print("Compare them with expected_findings.md.")


if __name__ == "__main__":
    main()