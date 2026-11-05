"""재현 진입점 템플릿. src/run_all.py 로 복사해 쓴다.
실행: python -m src.run_all  (작업 공간 루트에서)
"""
import time


def main():
    t0 = time.time()
    from src import clean, analyze          # noqa: WPS433

    clean.main()      # data/raw → data/clean, outputs/tables/cleaning_*.csv
    analyze.main()    # data/clean → outputs/tables, outputs/figures
    if hasattr(analyze, "sensitivity"):
        analyze.sensitivity()
    print(f"[run_all] 완료 {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
