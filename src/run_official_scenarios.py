from experiments.scenarios import run_and_export_official_scenarios


def main():
    output = run_and_export_official_scenarios()

    print("Official scenario export")
    print("-" * 40)
    print(f"scenarios defined: {len(output['scenarios'])}")
    print(f"per-run rows: {len(output['rows'])}")
    print(f"summary rows: {len(output['summary_rows'])}")
    print(f"saved per-run csv: {output['runs_path']}")
    print(f"saved summary csv: {output['summary_path']}")


if __name__ == "__main__":
    main()
