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
                \blogic\b|\bwire\b|\bint\b) |
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
        kind = m.lastgroup
        value = m.group()

        if kind == "SKIP":
            continue
        if kind == "OTHER":
            continue

        tokens.append((kind, value))

    tokens.append(("EOF", "EOF"))
    return tokens


# ============================================================
# PARSER BASE
# ============================================================

class Parser:
    def __init__(self, code):
        self.tokens = tokenize(code)
        self.pos = 0

    # ----------------------------
    def peek(self):
        if self.pos >= len(self.tokens):
            return ("EOF", "EOF")
        return self.tokens[self.pos]

    # ----------------------------
    def eat(self):
        tok = self.peek()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    # ============================================================
    # PARSE ENTRY
    # ============================================================
    def parse(self):
        items = []
        while True:
            tok = self.peek()
            if tok[0] == "EOF":
                break

            if tok[1] == "class":
                items.append(self.parse_class())
            elif tok[1] == "module":
                items.append(self.parse_module())
            else:
                self.eat()

        return {"type": "source", "items": items}

    # ============================================================
    # PARSE CLASS
    # ============================================================
    def parse_class(self):
        self.eat()  # class
        class_name = self.eat()[1]

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

        return {
            "type": "class",
            "name": class_name,
            "members": members
        }

    # ============================================================
    # PARSE FUNCTION
    # ============================================================
    def parse_function(self):
        self.eat()  # function
        return_type = self.eat()[1]  # usually void/int/logic
        name = self.eat()[1]

        # Parse arguments
        args = []
        if self.peek()[1] == "(":
            self.eat()
            arg_tokens = []
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                arg_tokens.append(self.eat()[1])
            self.eat()  # ')'
            args = arg_tokens

        # parse function body until endfunction
        body = []
        while self.peek()[1] != "endfunction" and self.peek()[0] != "EOF":
            body.append(self.eat()[1])
        if self.peek()[1] == "endfunction":
            self.eat()

        return {
            "type": "function",
            "name": name,
            "return_type": return_type,
            "args": args,
            "body_raw": " ".join(body)
        }

    # ============================================================
    # PARSE MODULE
    # ============================================================
    def parse_module(self):
        self.eat()  # module
        module_name = self.eat()[1]

        # -----------------------------
        # Parse ports
        # -----------------------------
        ports = []
        if self.peek()[1] == "(":
            self.eat()
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                tok = self.eat()[1]
                if tok != ",":
                    ports.append(tok)
            self.eat()  # ')'

        if self.peek()[1] == ";":
            self.eat()

        # -----------------------------
        # Parse body
        # -----------------------------
        signals = []
        functions = []
        always_blocks = []
        others = []

        while True:
            tok = self.peek()
            if tok[1] == "endmodule" or tok[0] == "EOF":
                break

            # --- signal declaration ---
            if tok[1] in ("logic", "wire", "int"):
                signals.append(self.parse_signal())
                continue

            # --- function ---
            if tok[1] == "function":
                functions.append(self.parse_function())
                continue

            # --- always block ---
            if tok[1] in ("always", "always_ff", "always_comb", "always_latch"):
                always_blocks.append(self.parse_always())
                continue

            others.append(self.eat()[1])

        if self.peek()[1] == "endmodule":
            self.eat()

        return {
            "type": "module",
            "name": module_name,
            "ports": ports,
            "signals": signals,
            "functions": functions,
            "always_blocks": always_blocks,
            "others_raw": " ".join(others),
        }

    # ============================================================
    # PARSE SIGNAL DECLARATION
    # ============================================================
    def parse_signal(self):
        sig_type = self.eat()[1]  # logic, wire, int
        bits = None
        names = []

        # width?
        if self.peek()[1] == "[":
            bracket = []
            while self.peek()[1] != "]":
                bracket.append(self.eat()[1])
            bracket.append(self.eat()[1])  # consume ']'
            bits = "".join(bracket)

        # names until semicolon
        while self.peek()[1] != ";" and self.peek()[0] != "EOF":
            tok = self.eat()[1]
            if tok != ",":
                names.append(tok)

        if self.peek()[1] == ";":
            self.eat()

        return {
            "type": "signal",
            "data_type": sig_type,
            "width": bits,
            "names": names
        }

    # ============================================================
    # PARSE ALWAYS BLOCK
    # ============================================================
    def parse_always(self):
        kind = self.eat()[1]  # always, always_ff, always_comb

        sensitivity = None
        if self.peek()[1] == "@":
            sens = []
            while self.peek()[1] != ")" and self.peek()[0] != "EOF":
                sens.append(self.eat()[1])
            sens.append(self.eat()[1])  # consume ')'
            sensitivity = " ".join(sens)

        # parse body: begin ... end
        body = []
        while not (self.peek()[1] == "end" or self.peek()[1] == "endmodule"):
            body.append(self.eat()[1])

        if self.peek()[1] == "end":
            self.eat()

        return {
            "type": "always",
            "kind": kind,
            "sensitivity": sensitivity,
            "body_raw": " ".join(body)
        }


# ============================================================
# TOP LEVEL
# ============================================================

def extract_ast(infile, outfile):
    with open(infile) as f:
        code = f.read()

    parser = Parser(code)
    ast = parser.parse()

    with open(outfile, "w") as f:
        json.dump(ast, f, indent=2)

    print(f"[OK] AST saved to {outfile}")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sv_ast_enhanced.py input.sv output.json")
        sys.exit(1)

    extract_ast(sys.argv[1], sys.argv[2])
