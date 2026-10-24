"""Disabled historical scorer: refusal/keyword matching is not an attack-success oracle.

See deliverables/d2/report/D2_EXPERIMENT_PLAN.md. A future attack evaluation needs native
trajectories and explicit attacker-goal/legitimate-utility labels. No historical
ASR or synthetic answer is promoted to a current result.
"""

def run_redteam(*args, **kwargs):
    raise RuntimeError("Legacy red-team scoring is disabled; define and review an attack-outcome protocol before collection.")

if __name__ == "__main__":
    run_redteam()
