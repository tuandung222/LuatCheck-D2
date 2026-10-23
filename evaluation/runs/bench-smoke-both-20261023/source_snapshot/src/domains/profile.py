"""Domain profile: every domain-specific element of the assistant as data.

A profile is a YAML file in ``config/domains/<profile_id>.yaml``. The agent core keeps
canonical actions (``ActionType``: SEARCH, READ, ANSWER, CLARIFY, REFUSE); the profile
only names them for the model, and supplies the prompts, document-ID convention,
domain guardrail patterns and L1 quantity vocabulary. Shared code must not hard-code
any of these.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from src.agent.state import ActionType

DEFAULT_PROFILE_ID = "labour_vi_2019"
PROFILE_DIR = Path(__file__).resolve().parents[2] / "config" / "domains"

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


class MessagesSpec(BaseModel):
    duplicate_query: str = Field(description="Observation for a repeated search; {read_tool}")
    already_read: str = Field(description="Observation for a repeated read")
    unretrieved_citation: str = Field(description="L1 provenance feedback; {doc_id}")
    repair_exhausted: str = Field(description="Refusal reason after the repair budget; {max_repairs}, {repair_feedback}")
    search_summary: str = Field(description="Audit summary of a search; {count}")

    @model_validator(mode="after")
    def _formattable(self) -> "MessagesSpec":
        self.duplicate_query.format(read_tool="x")
        self.unretrieved_citation.format(doc_id="x")
        self.repair_exhausted.format(max_repairs=1, repair_feedback="x")
        self.search_summary.format(count=1)
        return self


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
