.PHONY: install eval report clean

install:
	pip install uv && uv sync

eval:
	python -m src.runner
	python -m src.evals.code_based
	python -m src.evals.llm_judge

report:
	python -m src.report
	python -m src.viz

human-eval:
	python -m src.evals.human

clean:
	rm -rf data/outputs/* data/eval_results/* results/*.png results/leaderboard.md
