"""Domain profile: every domain-specific element of the assistant as data.

A profile is a YAML file in ``config/domains/<profile_id>.yaml``. The agent core keeps
canonical actions (``ActionType``: SEARCH, READ, ANSWER, CLARIFY, REFUSE); the profile
only names them for the model, and supplies the prompts, document-ID convention,
domain guardrail patterns and L1 quantity vocabulary. Shared code must not hard-code
any of these.
"""
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from src.agent.state import ActionType

DEFAULT_PROFILE_ID = "labour_vi_2019"
PROFILE_DIR = Path(__file__).resolve().parents[2] / "config" / "domains"
MESSAGE_PACK_DIR = PROFILE_DIR / "messages"

_TOOL_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROFILE_ID = re.compile(r"^[a-z0-9_]+$")
_TOKEN = re.compile(r"<<[a-z_]+>>")


class ToolSpec(BaseModel):
    name: str = Field(description="Name the model must use as the JSON `action` value")
    description: str = Field(description="Model-/client-facing description of the tool (also used by the MCP server)")

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        if not _TOOL_NAME.match(value):
            raise ValueError(f"Tool name {value!r} must be a plain identifier.")
        return value


class ToolsSpec(BaseModel):
    search: ToolSpec
    read: ToolSpec


class IdAlias(BaseModel):
    source: str = Field(description="Lowercase text to rewrite (after whitespace and case normalisation)")
    target: str
    position: Literal["prefix", "anywhere"] = "prefix"


class IdConvention(BaseModel):
    pattern: str = Field(description="Regex a canonical document ID must fully match")
    example: str = Field(description="An example canonical ID; must match `pattern`")
    whitespace_to: str = Field(default="_", description="Replacement for spaces when normalising a cited ID")
    aliases: List[IdAlias] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "IdConvention":
        if not re.fullmatch(self.pattern, self.example):
            raise ValueError(f"ID example {self.example!r} does not match pattern {self.pattern!r}.")
        return self


class L1Spec(BaseModel):
    quantity_units: List[str] = Field(min_length=1, description="Units checked by L1 exact-quantity matching; order is the regex alternation order")
    stopwords: List[str] = Field(default_factory=list)


class GuardrailSpec(BaseModel):
    patterns: List[str] = Field(default_factory=list, description="Domain-specific refusal patterns only; generic injection patterns live in guardrails.py")
    refusal_message: Optional[str] = Field(default=None, description="Overrides the shared safety-refusal text when set")

    @field_validator("patterns")
    @classmethod
    def _compile(cls, patterns: List[str]) -> List[str]:
        for pattern in patterns:
            re.compile(pattern)
        return patterns


# Messages that a profile may leave out: they come from the language pack config/domains/messages/<language>.yaml.
# name -> sample format arguments (also the placeholders a message may use). None = used verbatim.
PACK_MESSAGES: Dict[str, Optional[Dict[str, Any]]] = {
    "tool_budget_search": {"max_tool_calls": 1}, "tool_budget_read": {"max_tool_calls": 1},
    "steps_exhausted": {"max_steps": 1}, "tool_budget_exhausted": {"max_tool_calls": 1},
    "component_error_summary": {"kind": "x"}, "read_status": {"status": "x"},
    "search_not_found": {"query": "x"}, "document_not_found": {"doc_id": "x"},
    "l1_empty_answer_claim": None, "l1_empty_answer_feedback": None, "l1_missing_citation_feedback": None,
    "l1_unknown_citation": {"doc_id": "x"}, "l1_quote_mismatch": {"doc_id": "x"},
    "l1_unsupported_claims": {"count": 1, "claims": "x"},
    "nli_repair_feedback": {"count": 1, "threshold": 0.9, "pairs": "x"},
    "nli_pair_line": {"sentence": "x", "premise_id": "x", "probability": 0.5},
    "l2_repair_feedback": {"count": 1, "threshold": 0.5, "claims": "x"},
    "cache_l2_rejection": {"count": 1, "claims": "x"},
}


@lru_cache(maxsize=None)
def load_message_pack(language: str) -> Dict[str, str]:
    """Controller/tool/verifier messages for a language (config/domains/messages/<language>.yaml)."""
    path = MESSAGE_PACK_DIR / f"{language}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"No message pack for language {language!r}: {path} is missing "
                                "(add it, or set every message in the profile's own `messages:` block)")
    return {str(k): str(v) for k, v in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).items()}


class MessagesSpec(BaseModel):
    """Texts the controller and the verifiers write into observations, ledgers and repair feedback.

    The first five are required in every profile. All others are optional; a profile that leaves one out gets
    the text of its language pack (`load_message_pack`), see `DomainProfile`.
    """
    duplicate_query: str = Field(description="Observation for a repeated search; {read_tool}")
    already_read: str = Field(description="Observation for a repeated read")
    unretrieved_citation: str = Field(description="L1 provenance feedback; {doc_id}")
    repair_exhausted: str = Field(description="Refusal reason after the repair budget; {max_repairs}, {repair_feedback}")
    search_summary: str = Field(description="Audit summary of a search; {count}")

    tool_budget_search: Optional[str] = Field(default=None, description="Observation when the tool budget is spent (search action); {max_tool_calls}")
    tool_budget_read: Optional[str] = Field(default=None, description="Same, for the read action; {max_tool_calls}")
    steps_exhausted: Optional[str] = Field(default=None, description="Refusal reason when the step budget is spent; {max_steps}")
    tool_budget_exhausted: Optional[str] = Field(default=None, description="Refusal reason when the tool budget is spent on the last step; {max_tool_calls}")
    component_error_summary: Optional[str] = Field(default=None, description="Ledger summary of a failed model component; {kind}")
    read_status: Optional[str] = Field(default=None, description="Ledger summary of a read; {status}")
    search_not_found: Optional[str] = Field(default=None, description="Search result without hits; {query}")
    document_not_found: Optional[str] = Field(default=None, description="Read of an unknown ID; {doc_id}")
    l1_empty_answer_claim: Optional[str] = None
    l1_empty_answer_feedback: Optional[str] = None
    l1_missing_citation_feedback: Optional[str] = None
    l1_unknown_citation: Optional[str] = Field(default=None, description="{doc_id}")
    l1_quote_mismatch: Optional[str] = Field(default=None, description="{doc_id}")
    l1_unsupported_claims: Optional[str] = Field(default=None, description="{count}, {claims}")
    nli_repair_feedback: Optional[str] = Field(default=None, description="{count}, {threshold}, {pairs}")
    nli_pair_line: Optional[str] = Field(default=None, description="{sentence}, {premise_id}, {probability}")
    l2_repair_feedback: Optional[str] = Field(default=None, description="{count}, {threshold}, {claims}")
    cache_l2_rejection: Optional[str] = Field(default=None, description="{count}, {claims}")

    @model_validator(mode="after")
    def _formattable(self) -> "MessagesSpec":
        self.duplicate_query.format(read_tool="x")
        self.unretrieved_citation.format(doc_id="x")
        self.repair_exhausted.format(max_repairs=1, repair_feedback="x")
        self.search_summary.format(count=1)
        for name, sample in PACK_MESSAGES.items():
            text = getattr(self, name)
            if text is not None and sample is not None:
                try:
                    text.format(**sample)
                except (KeyError, IndexError, ValueError) as exc:
                    raise ValueError(f"messages.{name} {text!r} is not a valid template for {sorted(sample)}: {exc!r}") from exc
        return self

    def filled_from(self, pack: Dict[str, str]) -> "MessagesSpec":
        """Copy with every unset optional message taken from `pack`."""
        missing = [name for name in PACK_MESSAGES if getattr(self, name) is None and name not in pack]
        if missing:
            raise ValueError(f"Messages {missing} are neither set in the profile nor in its language pack.")
        values = {name: pack[name] for name in PACK_MESSAGES if getattr(self, name) is None}
        return MessagesSpec(**{**self.model_dump(), **values})


class DomainProfile(BaseModel):
    id: str
    display_name: str
    source_name: str = Field(description="Default source/document-set name used when a citation omits it")
    language: str
    corpus_path: Optional[str] = Field(default=None, description="Recommended corpus; retrieval.corpus_path in the app config is authoritative")
    out_of_scope_hint: str
    system_prompt: str = Field(description="Literal text; <<search_tool>>, <<read_tool>>, <<source_name>>, <<id_example>> and <<out_of_scope_hint>> are filled at load")
    repair_prompt: str = Field(description="str.format template with {repair_feedback}; same <<...>> tokens")
    tools: ToolsSpec
    ids: IdConvention
    l1: L1Spec
    guardrails: GuardrailSpec = Field(default_factory=GuardrailSpec)
    messages: MessagesSpec

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not _PROFILE_ID.match(value):
            raise ValueError("Profile id may contain only lowercase letters, digits and underscores.")
        return value

    @model_validator(mode="after")
    def _render(self) -> "DomainProfile":
        names = [self.tools.search.name, self.tools.read.name]
        reserved = {ActionType.ANSWER.value, ActionType.CLARIFY.value, ActionType.REFUSE.value}
        if len(set(names)) != 2 or set(names) & reserved:
            raise ValueError("Tool names must be distinct and must not reuse answer/clarify/refuse.")
        values = {"search_tool": names[0], "read_tool": names[1], "source_name": self.source_name,
                  "id_example": self.ids.example, "out_of_scope_hint": self.out_of_scope_hint}
        def fill(text: str) -> str:
            for key, value in values.items():
                text = text.replace(f"<<{key}>>", value)
            leftover = _TOKEN.search(text)
            if leftover:
                raise ValueError(f"Unknown prompt token {leftover.group(0)}.")
            return text
        self.system_prompt = fill(self.system_prompt)
        self.repair_prompt = fill(self.repair_prompt)
        self.repair_prompt.format(repair_feedback="x")
        if any(getattr(self.messages, name) is None for name in PACK_MESSAGES):
            self.messages = self.messages.filled_from(load_message_pack(self.language))
        return self

    # --- canonical action <-> model-facing name -------------------------------------------
    def model_action_name(self, action: ActionType) -> str:
        if action is ActionType.SEARCH:
            return self.tools.search.name
        if action is ActionType.READ:
            return self.tools.read.name
        return action.value

    @property
    def model_action_names(self) -> List[str]:
        return [self.model_action_name(a) for a in ActionType]

    def canonical_action(self, name: Any) -> Optional[ActionType]:
        """Map a model-supplied action name to its canonical action; None when it is not in this profile."""
        if not isinstance(name, str):
            return None
        for action in ActionType:
            if self.model_action_name(action) == name:
                return action
        return None

    # --- document IDs ----------------------------------------------------------------------
    def matches_id(self, doc_id: str) -> bool:
        return re.fullmatch(self.ids.pattern, str(doc_id)) is not None

    def normalize_id(self, doc_id: Any) -> str:
        did = str(doc_id).strip().replace(" ", self.ids.whitespace_to).lower()
        for alias in self.ids.aliases:
            if alias.position == "prefix":
                if did.startswith(alias.source):
                    did = alias.target + did[len(alias.source):]
            else:
                did = did.replace(alias.source, alias.target)
        return did

    # --- L1 ----------------------------------------------------------------------------------
    @property
    def quantity_pattern(self) -> str:
        units = "|".join(re.escape(unit).replace(r"\ ", r"\s+") for unit in self.l1.quantity_units)
        return r"\b\d+(?:[.,]\d+)?\s*(?:" + units + ")"

    @property
    def stopword_set(self) -> Set[str]:
        return set(self.l1.stopwords)


def load_profile(profile: Union[str, Path, None] = None) -> DomainProfile:
    """Load a profile by id (config/domains/<id>.yaml) or from an explicit YAML path."""
    ref = str(profile) if profile else DEFAULT_PROFILE_ID
    if "/" in ref or "\\" in ref or ref.endswith((".yaml", ".yml")):
        path = Path(ref)
    else:
        if not _PROFILE_ID.match(ref):
            raise ValueError(f"Invalid domain profile id {ref!r}.")
        path = PROFILE_DIR / f"{ref}.yaml"
    if not path.is_file():
        available = sorted(p.stem for p in PROFILE_DIR.glob("*.yaml"))
        raise FileNotFoundError(f"Domain profile not found: {path} (available: {available})")
    raw: Dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    loaded = DomainProfile(**raw)
    if path.parent == PROFILE_DIR and loaded.id != path.stem:
        raise ValueError(f"Profile id {loaded.id!r} must match its file name {path.stem!r}.")
    return loaded


def list_profiles() -> List[str]:
    return sorted(p.stem for p in PROFILE_DIR.glob("*.yaml"))
