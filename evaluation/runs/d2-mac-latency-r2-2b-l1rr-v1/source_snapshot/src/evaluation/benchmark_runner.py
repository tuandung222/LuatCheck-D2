"""Native-only notebook entry point. Test doubles are not empirical backends."""
from evaluation.run_eval import run_benchmark


class BenchmarkRunner:
    def __init__(self, agent=None, tasks_path="evaluation/benchmarks/bll2019_v1/tasks.json",
                 cold_cache_isolation=True, config_path="config/d2_native.yaml"):
        if agent is not None:
            raise ValueError("Empirical collection constructs a native client from config; injected unit fixtures are not accepted.")
        if not cold_cache_isolation:
            raise ValueError("The D2 protocol requires cold episodic memory.")
        self.tasks_path = tasks_path
        self.config_path = config_path

    def run(self, seeds=None, mode="l1_on", *, execute=False, output_dir=None,
            phase="pilot", task_review=None):
        return run_benchmark(self.tasks_path, seeds or [42, 123, 2026], mode,
                             execute=execute, output_dir=output_dir, phase=phase,
                             task_review=task_review, config_path=self.config_path)
