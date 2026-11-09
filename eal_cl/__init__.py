"""EAL-CL: emergent communication language.

Public API:
    Symbol                      # discrete learnable symbol
    Vocabulary                  # dynamic, versioned symbol set
    GrammarRule, Grammar        # structural composition rules (no hardcoded semantics)
    Language, LanguageVersion   # paired grammar+vocabulary, versioned
    Encoder, Decoder            # learnable concept <-> symbol mapping
    Message, Channel            # bidirectional message transport

No symbol meaning is hardcoded; semantics emerge through agent interaction.
"""

from .channel import Channel, Message
from .encoder import Decoder, Encoder, SymbolAssociation
from .grammar import Grammar, GrammarRule
from .language import Language, LanguageVersion
from .symbol import Symbol
from .vocabulary import Vocabulary

__all__ = [
    "Channel",
    "Decoder",
    "Encoder",
    "Grammar",
    "GrammarRule",
    "Language",
    "LanguageVersion",
    "Message",
    "Symbol",
    "SymbolAssociation",
    "Vocabulary",
]
