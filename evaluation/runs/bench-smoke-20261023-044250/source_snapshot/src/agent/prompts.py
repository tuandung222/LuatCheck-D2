"""
Prompt templates for the LuatCheck agent.

The prompt text is domain data: it lives in the domain profile (config/domains/<profile>.yaml) and is
used by the agent through ``agent.profile``. ``SYSTEM_PROMPT`` and ``REPAIR_PROMPT_TEMPLATE`` below are
the default (labour_vi_2019) profile's prompts, kept for callers that import the constants.
"""
from src.domains import load_profile

_DEFAULT_PROFILE = load_profile()

SYSTEM_PROMPT = _DEFAULT_PROFILE.system_prompt
REPAIR_PROMPT_TEMPLATE = _DEFAULT_PROFILE.repair_prompt
