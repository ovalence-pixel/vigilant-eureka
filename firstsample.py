import re
import json
import sys

# ------------------------------------------------------------
# TOKENIZER
# ------------------------------------------------------------

TOKEN_REGEX = re.compile(
    r"""
    (?P<KEYWORD>\bclass\b|\bendclass\b|\bmodule\b|\bendmodule\b|
                \bfunction\b|\bendfunction\b) |
    (?P<IDENT>[a-zA-Z_][a-zA-Z0-9_$]*) |
    (?P<NUMBER>\d+'[hdbo][0-9a-fA-F_]+|\d+) |
    (?P<STRING>"[^"]*") |
    (?P<SYMBOL>[\(\)\[\]\{\};,=:+\-*/<>]) |
    (?P<SKIP>\s+|//[^\n]*|/\*.*?\*/) |
    (?P<OTHER>.)
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE
)


def tokenize(code):
    tokens = []
    for m in TOKEN_REGEX.finditer(code):
        kind = m.lastgroup
        value = m.group()

        if kind == "SKIP":
            continue
        if kind == "OTHER":
            # ignore unknown but don't break stream
            continue

        tokens.append((kind, value))

    tokens.append(("EOF", "EOF"))
    return tokens


# ------------------------------------------------------------
# SAFE PARSER
# ------------------------------------------------------------

class Parser:
    def __init__(self, code):
        self.tokens = tokenize(code)
        self.pos = 0

    def safe_peek(self):
        """Safe peek never goes out of range."""
        if self.pos >= len(self.tokens):
            return ("EOF", "EOF")
        return self.tokens[self.pos]

    def safe_eat(self):
        """Safe eat: never goes out of range and always returns a token."""
        tok = self.safe_peek()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    # --------------------------------------------------------
    # MAIN PARSE ENTRY
    # --------------------------------------------------------

    def parse(self):
        items = []
        while True:
            tok = self.safe_peek()
            if tok[0] == "EOF":
                break

            if tok[1] == "class":
                items.append(self.parse_class())

            elif tok[1] == "module":
                items.append(self.parse_module())

            else:
                self.safe_eat()  # skip unknown top-level tokens
        return {"type": "source", "items": items}

    # --------------------------------------------------------
    # PARSE CLASS
    # --------------------------------------------------------

    def parse_class(self):
        self.safe_eat()  # 'class'
        name = self.safe_eat()[1]

        body_tokens = []
        while True:
            tok = self.safe_peek()
            if tok[1] == "endclass" or tok[0] == "EOF":
                break
            body_tokens.append(self.safe_eat()[1])

        if self.safe_peek()[1] == "endclass":
            self.safe_eat()

        return {
            "type": "class",
            "name": name,
            "body_raw": " ".join(body_tokens)
        }

    # --------------------------------------------------------
    # PARSE MODULE
    # --------------------------------------------------------

    def parse_module(self):
        self.safe_eat()  # 'module'
        name = self.safe_eat()[1]

        ports = []
        tok = self.safe_peek()

        if tok[1] == "(":
            self.safe_eat()  # '('
            while True:
                tok = self.safe_peek()
                if tok[1] == ")" or tok[0] == "EOF":
                    break

                if tok[1] != ",":
                    ports.append(tok[1])
                self.safe_eat()

            if self.safe_peek()[1] == ")":
                self.safe_eat()

        # consume optional semicolon
        if self.safe_peek()[1] == ";":
            self.safe_eat()

        # BODY
        body_tokens = []
        while True:
            tok = self.safe_peek()
            if tok[1] == "endmodule" or tok[0] == "EOF":
                break
            body_tokens.append(self.safe_eat()[1])

        if self.safe_peek()[1] == "endmodule":
            self.safe_eat()

        return {
            "type": "module",
            "name": name,
            "ports": ports,
            "body_raw": " ".join(body_tokens)
        }


# ------------------------------------------------------------
# TOP-LEVEL FUNCTION
# ------------------------------------------------------------

def extract_ast(infile, outfile):
    with open(infile, "r") as f:
        code = f.read()

    parser = Parser(code)
    ast = parser.parse()

    with open(outfile, "w") as f:
        json.dump(ast, f, indent=2)

    print(f"AST dumped to {outfile}")


# ------------------------------------------------------------
# CLI ENTRY
# ------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sv_ast_dump_fixed.py input.sv output.json")
        sys.exit(1)

    extract_ast(sys.argv[1], sys.argv[2])
