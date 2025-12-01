import re
import json
import sys

# ============================================================
# TOKENIZER
# ============================================================

TOKEN_REGEX = re.compile(
    r"""
    (?P<KEYWORD>\bclass\b|\bendclass\b|\bmodule\b|\bendmodule\b|
                \bfunction\b|\bendfunction\b|
                \balways\b|\balways_ff\b|\balways_comb\b|\balways_latch\b|
                \binput\b|\boutput\b|\binout\b|
                \blogic\b|\bwire\b|\bint\b|
                \bif\b|\belse\b|\bcase\b|\bendcase\b|\bbegin\b|\bend\b) |
    (?P<IDENT>[a-zA-Z_][a-zA-Z0-9_$]*) |
    (?P<NUMBER>\d+'[hdbo][0-9a-fA-F_]+|\d+) |
    (?P<STRING>"[^"]*") |
    (?P<SYMBOL>[\(\)\[\]\{\};,=:+\-*/<>@&|!]) |
    (?P<SKIP>\s+|//[^\n]*|/\*.*?\*/) |
    (?P<OTHER>.)
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE
)


def tokenize(code):
    tokens = []
    for m in TOKEN_REGEX.finditer(code):
        k = m.lastgroup
        v = m.group()
        if k == "SKIP" or k == "OTHER":
            continue
        tokens.append((k, v))
    tokens.append(("EOF", "EOF"))
    return tokens


# ============================================================
# PARSER
# ============================================================

class Parser:
    def __init__(self, code):
        self.tokens = tokenize(code)
        self.pos = 0

    def peek(self):
        if self.pos >= len(self.tokens):
            return ("EOF", "EOF")
        return self.tokens[self.pos]

    def eat(self):
        t = self.peek()
        if self.pos < len(self.tokens):
            self.pos += 1
        return t

    # ========================================================
    # ROOT PARSER
    # ========================================================
    def parse(self):
        items = []
        while True:
            tok = self.peek()
            if tok[0] == "EOF":
                break
            if tok[1] == "module":
                items.append(self.parse_module())
            elif tok[1] == "class":
                items.append(self.parse_class())
            else:
                self.eat()
        return {"type": "source", "items": items}

    # ========================================================
    # CLASS PARSING
    # ========================================================
    def parse_class(self):
        self.eat()  # 'class'
        name = self.eat()[1]
        members = []
        while True:
            tok = self.peek()
            if tok[1] == "endclass" or tok[0] == "EOF":
                break
            if tok[1] == "function":
                members.append(self.parse_function())
            else:
                self.eat()
        if self.peek()[1] == "endclass":
            self.eat()
        return {"type": "class", "name": name, "members": members}

    # ========================================================
    # FUNCTION PARSING
    # ========================================================
    def parse_function(self):
        self.eat()  # 'function'
        return_type = self.eat()[1]
        name = self.eat()[1]

        args = []
        if self.peek()[1] == "(":
            self.eat()
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                tok = self.eat()[1]
                if tok != ",":
                    args.append(tok)
            self.eat()  # ')'

        body = self.parse_block(end_tokens=("endfunction",))
        return {
            "type": "function",
            "name": name,
            "return_type": return_type,
            "args": args,
            "body": body
        }

    # ========================================================
    # MODULE PARSING
    # ========================================================
    def parse_module(self):
        self.eat()  # 'module'
        name = self.eat()[1]

        ports = []
        if self.peek()[1] == "(":
            self.eat()
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                t = self.eat()[1]
                if t != ",":
                    ports.append(t)
            self.eat()  # ')'

        if self.peek()[1] == ";":
            self.eat()

        body = self.parse_block(end_tokens=("endmodule",))
        return {"type": "module", "name": name, "ports": ports, "body": body}

    # ========================================================
    # GENERIC BLOCK PARSING
    # ========================================================
    def parse_block(self, end_tokens=("end",)):
        elements = []
        while True:
            tok = self.peek()
            if tok[1] in end_tokens or tok[0] == "EOF":
                break

            # Signals
            if tok[1] in ("logic", "wire", "int"):
                elements.append(self.parse_signal())
                continue

            # Functions
            if tok[1] == "function":
                elements.append(self.parse_function())
                continue

            # Always blocks
            if tok[1] in ("always", "always_ff", "always_comb", "always_latch"):
                elements.append(self.parse_always())
                continue

            # Begin / end nested block
            if tok[1] == "begin":
                self.eat()
                elements.append({"type": "block", "body": self.parse_block(end_tokens=("end",))})
                if self.peek()[1] == "end":
                    self.eat()
                continue

            # If / else
            if tok[1] == "if":
                elements.append(self.parse_if())
                continue

            # Case
            if tok[1] == "case":
                elements.append(self.parse_case())
                continue

            # Other statement
            elements.append(self.parse_statement())

        return elements

    # ========================================================
    # SIGNAL PARSING
    # ========================================================
    def parse_signal(self):
        sig_type = self.eat()[1]
        width = None
        if self.peek()[1] == "[":
            w = []
            while self.peek()[1] != "]":
                w.append(self.eat()[1])
            w.append(self.eat()[1])  # ']'
            width = "".join(w)

        names = []
        while self.peek()[1] != ";" and self.peek()[0] != "EOF":
            tok = self.eat()[1]
            if tok != ",":
                names.append(tok)

        if self.peek()[1] == ";":
            self.eat()

        return {"type": "signal", "data_type": sig_type, "width": width, "names": names}

    # ========================================================
    # ALWAYS BLOCK PARSING
    # ========================================================
    def parse_always(self):
        kind = self.eat()[1]
        sensitivity = None
        if self.peek()[1] == "@":
            s = []
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                s.append(self.eat()[1])
            s.append(self.eat()[1])  # ')'
            sensitivity = " ".join(s)
        body = self.parse_block()
        return {"type": "always", "kind": kind, "sensitivity": sensitivity, "body": body}

    # ========================================================
    # IF / ELSE PARSING
    # ========================================================
    def parse_if(self):
        self.eat()  # 'if'
        cond = []
        if self.peek()[1] == "(":
            self.eat()
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                cond.append(self.eat()[1])
            self.eat()  # ')'
        then_block = self.parse_block()
        else_block = None
        if self.peek()[1] == "else":
            self.eat()
            else_block = self.parse_block()
        return {"type": "if", "cond": "".join(cond), "then": then_block, "else": else_block}

    # ========================================================
    # CASE PARSING
    # ========================================================
    def parse_case(self):
        self.eat()  # 'case'
        expr = []
        while self.peek()[1] != "\n" and self.peek()[0] != "EOF":
            expr.append(self.eat()[1])
        body = self.parse_block(end_tokens=("endcase",))
        if self.peek()[1] == "endcase":
            self.eat()
        return {"type": "case", "expr": "".join(expr), "body": body}

    # ========================================================
    # GENERIC STATEMENT PARSING
    # ========================================================
    def parse_statement(self):
        stmt = []
        while self.peek()[1] not in (";", "end", "begin", "if", "case") and self.peek()[0] != "EOF":
            stmt.append(self.eat()[1])
        if self.peek()[1] == ";":
            self.eat()
        return {"type": "statement", "code": " ".join(stmt)}


# ============================================================
# TOP LEVEL FUNCTION
# ============================================================

def extract_ast(infile, outfile):
    with open(infile) as f:
        code = f.read()

    parser = Parser(code)
    ast = parser.parse()

    with open(outfile, "w") as f:
        json.dump(ast, f, indent=2)

    print(f"AST saved to {outfile}")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sv_ast_hierarchical.py input.sv output.json")
        sys.exit(1)
    extract_ast(sys.argv[1], sys.argv[2])
