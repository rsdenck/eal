"""EAL-PL parser: turns a token stream into an AST.

Recursive-descent parser for the original EAL-PL grammar:

  program     := statement*
  statement   := bind_stmt | mut_stmt | fn_stmt | if_stmt | loop_stmt
               | return_stmt | print_stmt | expr_stmt | block_stmt
  bind_stmt   := "bind" IDENT (":" type)? "=" expression ";"
  mut_stmt    := "mut" IDENT (":" type)? "=" expression ";"
  fn_stmt     := "fn" IDENT "(" params ")" block
  params      := (IDENT ":" type) ("," IDENT ":")*
  if_stmt     := "if" expression block ("else" block)?
  loop_stmt   := "loop" block
  return_stmt := "return" expression? ";"
  print_stmt  := "print" expression ";"
  expr_stmt   := expression ";"
  block       := "{" statement* "}"
  expression  := equality
  equality    := comparison (("==" | "!=") comparison)*
  comparison  := addition ((">" | "<" | ">=" | "<=") addition)*
  addition    := multiplication (("+" | "-") multiplication)*
  multiplication := unary (("*" | "/") unary)*
  unary       := ("!" | "-") unary | primary
  primary     := IDENT | NUMBER | STRING | "true" | "false"
               | "(" expression ")" | call
  call        := IDENT "(" arguments ")"
  arguments   := expression ("," expression)*
  type        := "int" | "bool" | "string" | "void"
"""

from __future__ import annotations

from . import ast as pl_ast
from .errors import ParseError, SourceLocation
from .tokens import (TT_BIND, TT_BREAK, TT_COLON, TT_COMMA, TT_CONTINUE,
                     TT_ELSE, TT_EOF, TT_FALSE, TT_FN, TT_IDENT, TT_IF,
                     TT_INT, TT_INT_TYPE, TT_LBRACE, TT_LOOP, TT_LPAREN,
                     TT_ASSIGN, TT_MINUS, TT_MUT, TT_PRINT, TT_RBRACE,
                     TT_RPAREN, TT_RETURN, TT_SEMICOLON, TT_STRING,
                     TT_TRUE, TT_VOID_TYPE, Token, TT_EQ, TT_NE, TT_LT,
                     TT_GT, TT_LE, TT_GE, TT_PLUS, TT_STAR, TT_SLASH,
                     TT_BANG)

PRECEDENCE: dict[str, int] = {
    "=": 1,
    "==": 2, "!=": 2,
    "<": 3, "<=": 3, ">": 3, ">=": 3,
    "+": 4, "-": 4,
    "*": 5, "/": 5,
}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.current = 0

    # -- low level --------------------------------------------------------

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _at_end(self) -> bool:
        return self._peek().type == TT_EOF

    def _advance(self) -> Token:
        token = self._peek()
        if not self._at_end():
            self.current += 1
        return token

    def _check(self, token_type: str) -> bool:
        if self._at_end():
            return False
        return self._peek().type == token_type

    def _match(self, *types: str) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise ParseError(message, SourceLocation(
            file="<eal>", line=token.line, column=token.column))

    def _location(self) -> SourceLocation:
        token = self._peek()
        return SourceLocation(file="<eal>", line=token.line,
                              column=token.column)

    # -- entry point ------------------------------------------------------

    def parse(self) -> pl_ast.Program:
        statements = []
        while not self._at_end():
            statements.append(self._statement())
        return pl_ast.Program(
            location=self._location(), statements=statements)

    # -- statements -------------------------------------------------------

    def _statement(self) -> Any:
        if self._match(TT_BIND):
            return self._bind_stmt()
        if self._match(TT_MUT):
            return self._mut_stmt()
        if self._match(TT_BREAK):
            loc = self._location()
            self._consume(TT_SEMICOLON, "expected ';' after 'break'")
            return pl_ast.BreakStmt(location=loc)
        if self._match(TT_CONTINUE):
            loc = self._location()
            self._consume(TT_SEMICOLON, "expected ';' after 'continue'")
            return pl_ast.ContinueStmt(location=loc)
        if self._match(TT_FN):
            return self._fn_stmt()
        if self._match(TT_IF):
            return self._if_stmt()
        if self._match(TT_LOOP):
            return self._loop_stmt()
        if self._match(TT_RETURN):
            return self._return_stmt()
        if self._match(TT_PRINT):
            return self._print_stmt()
        if self._check(TT_LBRACE):
            return self._block_stmt()
        return self._expr_stmt()

    def _bind_stmt(self) -> pl_ast.BindStmt:
        name_token = self._consume(TT_IDENT, "expected variable name after 'bind'")
        type_annotation = None
        if self._match(TT_COLON):
            type_annotation = self._type()
        self._consume(TT_ASSIGN, "expected '=' after variable name")
        value = self._expression()
        self._consume(TT_SEMICOLON, "expected ';' after expression")
        return pl_ast.BindStmt(location=name_token.location, name=name_token.lexeme,
                               type_annotation=type_annotation, value=value)

    def _mut_stmt(self) -> pl_ast.MutStmt:
        name_token = self._consume(TT_IDENT, "expected variable name after 'mut'")
        type_annotation = None
        if self._match(TT_COLON):
            type_annotation = self._type()
        self._consume(TT_ASSIGN, "expected '=' after variable name")
        value = self._expression()
        self._consume(TT_SEMICOLON, "expected ';' after expression")
        return pl_ast.MutStmt(location=name_token.location, name=name_token.lexeme,
                              type_annotation=type_annotation, value=value)

    def _type(self) -> str:
        token = self._peek()
        if self._match(TT_INT_TYPE, TT_BOOL_TYPE, TT_STRING_TYPE, TT_VOID_TYPE):
            return token.lexeme
        raise ParseError("expected type", SourceLocation(
            file="<eal>", line=token.line, column=token.column))

    def _fn_stmt(self) -> pl_ast.FnStmt:
        name_token = self._consume(TT_IDENT, "expected function name after 'fn'")
        self._consume(TT_LPAREN, "expected '(' after function name")
        params = []
        if not self._check(TT_RPAREN):
            while True:
                pname_token = self._consume(TT_IDENT, "expected parameter name")
                ptype = None
                if self._match(TT_COLON):
                    ptype = self._type()
                params.append((pname_token.lexeme, ptype))
                if not self._match(TT_COMMA):
                    break
        self._consume(TT_RPAREN, "expected ')' after parameters")
        return_type = None
        if self._match(TT_COLON):
            return_type = self._type()
        body = self._block_stmt()
        return pl_ast.FnStmt(location=name_token.location, name=name_token.lexeme,
                             params=params, return_type=return_type, body=body)

    def _if_stmt(self) -> pl_ast.IfStmt:
        condition = self._expression()
        then_branch = self._block_stmt()
        else_branch = None
        if self._match(TT_ELSE):
            if self._match(TT_IF):
                else_branch = self._if_stmt()
            else:
                else_branch = self._block_stmt()
        return pl_ast.IfStmt(location=self._location(), condition=condition,
                             then_branch=then_branch, else_branch=else_branch)

    def _loop_stmt(self) -> pl_ast.LoopStmt:
        loc = self._location()
        body = self._block_stmt()
        return pl_ast.LoopStmt(location=loc, body=body)

    def _return_stmt(self) -> pl_ast.ReturnStmt:
        loc = self._location()
        value = None
        if not self._check(TT_SEMICOLON):
            value = self._expression()
        self._consume(TT_SEMICOLON, "expected ';' after return")
        return pl_ast.ReturnStmt(location=loc, value=value)

    def _print_stmt(self) -> pl_ast.PrintStmt:
        loc = self._location()
        expr = self._expression()
        self._consume(TT_SEMICOLON, "expected ';' after print")
        return pl_ast.PrintStmt(location=loc, expression=expr)

    def _block_stmt(self) -> pl_ast.BlockStmt:
        loc = self._location()
        self._consume(TT_LBRACE, "expected '{' to start block")
        statements = []
        while not self._check(TT_RBRACE) and not self._at_end():
            statements.append(self._statement())
        self._consume(TT_RBRACE, "expected '}' after block")
        return pl_ast.BlockStmt(location=loc, statements=statements)

    def _expr_stmt(self) -> pl_ast.ExprStmt:
        loc = self._location()
        expr = self._expression()
        self._consume(TT_SEMICOLON, "expected ';' after expression")
        return pl_ast.ExprStmt(location=loc, expression=expr)

    # -- expressions (precedence climbing) --------------------------------

    def _expression(self) -> Any:
        return self._parse_expression(0)

    def _parse_expression(self, min_prec: int) -> Any:
        left = self._unary()
        while not self._at_end():
            token = self._peek()
            prec = PRECEDENCE.get(token.lexeme)
            if prec is None or prec < min_prec:
                break
            self._advance()
            if token.lexeme == "=" and isinstance(left, pl_ast.Variable):
                # Variable assignment: x = expr
                right = self._parse_expression(prec + 1)
                return pl_ast.Assignment(location=token.location,
                                         name=left.name, value=right)
            right = self._parse_expression(prec + 1)
            left = pl_ast.Binary(location=token.location, left=left,
                                 operator=token.lexeme, right=right)
        return left

    def _unary(self) -> Any:
        token = self._peek()
        if self._check(TT_BANG) or self._check(TT_MINUS):
            self._advance()
            operand = self._unary()
            return pl_ast.Unary(location=token.location, operator=token.lexeme,
                                operand=operand)
        return self._primary()

    def _primary(self) -> Any:
        if self._match(TT_INT):
            token = self._peek()
            # token is EOF now because _match advanced past INT; retrieve
            # the consumed token from one position back.
            consumed = self.tokens[self.current - 1]
            return pl_ast.Literal(location=consumed.location, value=int(consumed.lexeme))
        if self._match(TT_STRING):
            consumed = self.tokens[self.current - 1]
            return pl_ast.Literal(location=consumed.location, value=consumed.lexeme)
        if self._match(TT_TRUE):
            return pl_ast.Literal(location=self.tokens[self.current - 1].location, value=True)
        if self._match(TT_FALSE):
            return pl_ast.Literal(location=self.tokens[self.current - 1].location, value=False)
        if self._match(TT_IDENT):
            name_token = self.tokens[self.current - 1]
            # function call?
            if self._match(TT_LPAREN):
                args = []
                if not self._check(TT_RPAREN):
                    while True:
                        args.append(self._expression())
                        if not self._match(TT_COMMA):
                            break
                self._consume(TT_RPAREN, "expected ')' after arguments")
                return pl_ast.Call(location=name_token.location,
                                   callee=name_token.lexeme, arguments=args)
            return pl_ast.Variable(location=name_token.location,
                                   name=name_token.lexeme)
        if self._match(TT_LPAREN):
            expr = self._expression()
            self._consume(TT_RPAREN, "expected ')' after expression")
            return expr
        token = self._peek()
        raise ParseError(f"unexpected token {token.lexeme!r}",
                         SourceLocation(file="<eal>", line=token.line,
                                        column=token.column))
