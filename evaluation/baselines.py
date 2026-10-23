"""Diagnostic baselines for the D2 matrix: the same Bonsai controller WITHOUT tools.

  closed_book   system prompt of the domain profile + a short disclosed note (config/benchmark/variants.yaml `baselines`), the
                question only; no tools, no documents. The model may only answer / clarify / refuse.
  oracle        as closed_book, plus the full text of the task's gold records given up front, in the observation format the read
                tool returns ("[OBSERVATION_TOOL_RESULT]\\n<json>", passive data like every observation). Gold is used BY DESIGN:
                this is a reading / reasoning ceiling with perfect retrieval, never a system variant. Answerable tasks only
                (refuse tasks have no gold context and are not scheduled for it).

Both reuse the real components: LuatCheckAgent's loop, guardrails, domain profile, LlamaCppLLMClient with constrained JSON decoding
(action schema restricted to answer / clarify / refuse via NativeLLMClient.restrict_actions), the real read tool to render the oracle
observations, and the runner's execute_trial (same row schema, judge, analysis). Verification is off (L1 is not applied). A
search/read action is impossible under the restricted schema and, if it ever appeared, is an execution error, never a tool call.
Nothing is canned: no assistant turn is fabricated; every answer comes from real inference.

`uses_gold` is True only for OracleBaselineAgent: it is the single place where gold ids enter an agent call, through prepare_trial.
"""
import json
from typing import Any, Dict, List, Optional

from src.agent.loop import OBSERVATION_PREFIX, LuatCheckAgent
from src.agent.state import ActionType, CaseLedger
from src.memory.ledger import CaseLedgerManager
from src.security.guardrails import SecurityGuardrails

BASELINE_KINDS = ("closed_book", "oracle")
ALLOWED_ACTIONS = (ActionType.ANSWER, ActionType.CLARIFY, ActionType.REFUSE)


class BaselineAgent(LuatCheckAgent):
    """No-tool controller. Subclasses decide whether documents are given."""
    kind = ""
    uses_gold = False

    def __init__(self, config, baseline_spec: Dict[str, Any]):
        super().__init__(config=config, verification_mode="off", l2_use_slm=False)
        self.baseline_spec = baseline_spec
        self.llm_client.restrict_actions(ALLOWED_ACTIONS)
        self.addendum = str(baseline_spec["prompt_addendum"]).strip()

    def system_prompt(self) -> str:
        return self.profile.system_prompt.rstrip() + "\n\n" + self.addendum

    def _initial_messages(self, user_query: str, pasted_doc: Optional[str], ledger: CaseLedger) -> List[Dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": SecurityGuardrails.wrap_untrusted_input(user_query, pasted_doc)}]

    def _tool_unavailable(self, run, name: str) -> None:
        self._finish(run.ledger, "error", self._error_output(f"The model asked for the tool {name!r}, which this baseline does not have.",
                                                            "model_output_error"))

    def _act_search(self, run, agent_resp, tool_args) -> None:
        self._tool_unavailable(run, "search")

    def _act_read(self, run, agent_resp, tool_args) -> None:
        self._tool_unavailable(run, "read")


class ClosedBookBaselineAgent(BaselineAgent):
    kind = "closed_book"


class OracleBaselineAgent(BaselineAgent):
    kind = "oracle"
    uses_gold = True   # the one explicit entry of gold ids into an agent call (see tests: only this class may have it)

    def __init__(self, config, baseline_spec):
        super().__init__(config, baseline_spec)
        self._gold_ids: List[str] = []

    def prepare_trial(self, task: Dict[str, Any]) -> None:
        self._gold_ids = [str(i) for i in task.get("ground_truth_article_ids", [])]

    def _initial_messages(self, user_query: str, pasted_doc: Optional[str], ledger: CaseLedger) -> List[Dict[str, str]]:
        blocks = []
        for doc_id in self._gold_ids:
            observation = self._read(doc_id)   # the real read tool: same JSON the controller would receive after a read action
            if observation.get("status") != "success":
                raise ValueError(f"oracle context: gold record {doc_id} could not be read: {observation}")
            CaseLedgerManager.add_retrieved_article(ledger, doc_id, observation.get("full_content", ""))
            blocks.append(OBSERVATION_PREFIX + json.dumps(observation, ensure_ascii=False))
        ledger.audit_events.append({"event": "oracle_context", "article_ids": list(self._gold_ids),
                                    "note": "gold records supplied up front; no tool call"})
        user = SecurityGuardrails.wrap_untrusted_input(user_query, pasted_doc)
        if blocks:
            user += "\n\n" + "\n\n".join(blocks)
        return [{"role": "system", "content": self.system_prompt()}, {"role": "user", "content": user}]


def build_baseline_agent(config, baseline_spec: Dict[str, Any]) -> BaselineAgent:
    kinds = {"closed_book": ClosedBookBaselineAgent, "oracle": OracleBaselineAgent}
    kind = baseline_spec.get("kind")
    if kind not in kinds:
        raise ValueError(f"unknown baseline kind {kind!r}; known: {sorted(kinds)}")
    return kinds[kind](config, baseline_spec)
