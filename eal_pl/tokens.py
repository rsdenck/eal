"""EAL-PL lexer: turns source text into a stream of tokens.

The token set defines the original EAL-PL grammar vocabulary
(bind / mut / fn / loop / return / print / if / else / true / false / int /
bool / string / void). This is an original keyword set, not a rename of
Python, Rust or Go.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .errors import EALPlError, LexerError, SourceLocation


# Token types
TT_INT = "INT"
TT_FLOAT = "FLOAT"
TT_STRING = "STRING"
TT_IDENT = "IDENT"
TT_TRUE = "TRUE"
TT_FALSE = "FALSE"
TT_BIND = "BIND"      # bind x = 5   (immutable by default)
TT_MUT = "MUT"        # mut x = 5    (mutable)
TT_FN = "FN"          # fn name(...) { ... }
TT_RETURN = "RETURN"
TT_PRINT = "PRINT"
TT_IF = "IF"
TT_ELSE = "ELSE"
TT_LOOP = "LOOP"
TT_BREAK = "BREAK"
TT_CONTINUE = "CONTINUE"
TT_INT_TYPE = "INT_TYPE"
TT_BOOL_TYPE = "BOOL_TYPE"
TT_STRING_TYPE = "STRING_TYPE"
TT_VOID_TYPE = "VOID_TYPE"
TT_ASSIGN = "ASSIGN"  # =
TT_PLUS = "PLUS"
TT_MINUS = "MINUS"
TT_STAR = "STAR"
TT_SLASH = "SLASH"
TT_BANG = "BANG"      # !
TT_EQ = "EQ"          # ==
TT_NE = "NE"          # !=
TT_LT = "LT"
TT_GT = "GT"
TT_LE = "LE"
TT_GE = "GE"
TT_LPAREN = "LPAREN"
TT_RPAREN = "RPAREN"
TT_LBRACE = "LBRACE"
TT_RBRACE = "RBRACE"
TT_COMMA = "COMMA"
TT_SEMICOLON = "SEMICOLON"
TT_COLON = "COLON"
TT_ARROW = "ARROW"    # -> (type annotation hint)
TT_EOF = "EOF"

KEYWORDS: dict[str, str] = {
    "bind": TT_BIND,
    "mut": TT_MUT,
    "fn": TT_FN,
    "return": TT_RETURN,
    "print": TT_PRINT,
    "if": TT_IF,
    "else": TT_ELSE,
    "loop": TT_LOOP,
    "break": TT_BREAK,
    "continue": TT_CONTINUE,
    "true": TT_TRUE,
    "false": TT_FALSE,
    "int": TT_INT_TYPE,
    "bool": TT_BOOL_TYPE,
    "string": TT_STRING_TYPE,
    "void": TT_VOID_TYPE,
}


@dataclass(frozen=True)
class Token:
    type: str
    lexeme: str
    line: int
    column: int

    @property
    def location(self) -> SourceLocation:
        return SourceLocation(file="<eal>", line=self.line, column=self.column)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Token({self.type}, {self.lexeme!r}, {self.line}:{self.column})"


class Lexer:
    def __init__(self, source: str, file: str = "<eal>") -> None:
        self.source = source
        self.file = file
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1

    # -- scanning ---------------------------------------------------------

    def _at_end(self) -> bool:
        return self.current >= len(self.source)

    def _advance(self) -> str:
        ch = self.source[self.current]
        self.current += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _location(self) -> SourceLocation:
        return SourceLocation(file=self.file, line=self.line,
                              column=self.column)

    def _skip_whitespace(self) -> None:
        while not self._at_end():
            ch = self.source[self.current]
            if ch in " \t\r":
                self._advance()
            elif ch == "\n":
                self._advance()
            elif ch == "/" and self.source[self.current + 1
                                         if self.current + 1 < len(self.source)
                                         else self.current] == "/":
                # line comment
                while not self._at_end() and self.source[self.current] != "\n":
                    self._advance()
            else:
                break

    def _read_number(self, loc: SourceLocation) -> Token:
        is_float = False
        while not self._at_end() and self.source[self.current].isdigit():
            self._advance()
        if (not self._at_end() and self.source[self.current] == "." and
                self.current + 1 < len(self.source) and
                self.source[self.current + 1].isdigit()):
            is_float = True
            self._advance()  # consume '.'
            while not self._at_end() and self.source[self.current].isdigit():
                self._advance()
        text = self.source[self.start:self.current]
        return Token(TT_FLOAT if is_float else TT_INT, text, loc.line,
                     loc.column)

    def _read_string(self, loc: SourceLocation) -> Token:
        self._advance()  # opening quote
        chars: List[str] = []
        while not self._at_end() and self.source[self.current] != '"':
            if self.source[self.current] == "\n":
                raise LexerError("unterminated string", loc)
            chars.append(self._advance())
        if self._at_end():
            raise LexerError("unterminated string", loc)
        self._advance()  # closing quote
        return Token(TT_STRING, "".join(chars), loc.line, loc.column)

    def _read_identifier(self, loc: SourceLocation) -> Token:
        while (not self._at_end() and
               (self.source[self.current].isalnum()
                or self.source[self.current] == "_")):
            self._advance()
        text = self.source[self.start:self.current]
        typ = KEYWORDS.get(text, TT_IDENT)
        return Token(typ, text, loc.line, loc.column)

    # -- public API -------------------------------------------------------

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while not self._at_end():
            self._skip_whitespace()
            if self._at_end():
                break
            self.start = self.current
            loc = self._location()
            ch = self.source[self.current]

            if ch.isdigit():
                tokens.append(self._read_number(loc))
                continue
            if ch == '"':
                tokens.append(self._read_string(loc))
                continue
            if ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier(loc))
                continue

            # two-character tokens first
            two = ch + self._peek_next()
            col_at_start = loc.column
            if two == "==":
                self._advance()
                self._advance()
                tokens.append(Token(TT_EQ, "==", loc.line, col_at_start))
                continue
            if two == "!=":
                self._advance()
                self._advance()
                tokens.append(Token(TT_NE, "!=", loc.line, col_at_start))
                continue
            if two == "<=":
                self._advance()
                self._advance()
                tokens.append(Token(TT_LE, "<=", loc.line, col_at_start))
                continue
            if two == ">=":
                self._advance()
                self._advance()
                tokens.append(Token(TT_GE, ">=", loc.line, col_at_start))
                continue
            self._advance()
            if ch == "=":
                tokens.append(Token(TT_ASSIGN, "=", loc.line, col_at_start))
            elif ch == "+":
                tokens.append(Token(TT_PLUS, "+", loc.line, col_at_start))
            elif ch == "-":
                tokens.append(Token(TT_MINUS, "-", loc.line, col_at_start))
            elif ch == "*":
                tokens.append(Token(TT_STAR, "*", loc.line, col_at_start))
            elif ch == "/":
                tokens.append(Token(TT_SLASH, "/", loc.line, col_at_start))
            elif ch == "!":
                tokens.append(Token(TT_BANG, "!", loc.line, col_at_start))
            elif ch == "<":
                tokens.append(Token(TT_LT, "<", loc.line, col_at_start))
            elif ch == ">":
                tokens.append(Token(TT_GT, ">", loc.line, col_at_start))
            elif ch == "(":
                tokens.append(Token(TT_LPAREN, "(", loc.line, col_at_start))
            elif ch == ")":
                tokens.append(Token(TT_RPAREN, ")", loc.line, col_at_start))
            elif ch == "{":
                tokens.append(Token(TT_LBRACE, "{", loc.line, col_at_start))
            elif ch == "}":
                tokens.append(Token(TT_RBRACE, "}", loc.line, col_at_start))
            elif ch == ",":
                tokens.append(Token(TT_COMMA, ",", loc.line, col_at_start))
            elif ch == ";":
                tokens.append(Token(TT_SEMICOLON, ";", loc.line, col_at_start))
            elif ch == ":":
                tokens.append(Token(TT_COLON, ":", loc.line, col_at_start))
            else:
                raise LexerError(
                    f"unexpected character {ch!r}",
                    SourceLocation(file=self.file, line=loc.line,
                                   column=col_at_start),
                )

        tokens.append(Token(TT_EOF, "", self.line, self.column))
        return tokens
