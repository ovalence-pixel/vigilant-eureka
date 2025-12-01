// Example SystemVerilog class
class my_class;
    // Class properties
    int id;
    string name;

    // Constructor
    function new(int id_val, string name_val);
        id   = id_val;
        name = name_val;
    endfunction

    // Method
    function void display();
        $display("ID=%0d, Name=%s", id, name);
    endfunction
endclass


// Module with 10 ports and class declaration
module top_module(
    input  logic clk,
    input  logic rst_n,
    input  logic [7:0] a,
    input  logic [7:0] b,
    output logic [7:0] sum,
    input  logic enable,
    output logic ready,
    input  logic valid,
    output logic done,
    input  logic trigger
);

    // Declare and instantiate the class inside the module
    my_class obj;

    initial begin
        obj = new(1, "example");
        obj.display();
    end

    // Simple logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sum  <= 0;
            ready <= 0;
            done <= 0;
        end else if (enable & valid) begin
            sum <= a + b;
            ready <= 1;
            done <= trigger;
        end
    end

endmodule# -------------------------------------------------------------------
# SIMPLE RECURSIVE PARSER FOR: 
#  - class ... endclass
#  - module ... endmodule
# -------------------------------------------------------------------

class SVParser:
    def __init__(self, code):
        self.tokens = tokenize(code)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def eat(self, expected=None):
        token = self.peek()
        if expected and token[1] != expected:
            raise SyntaxError(f"Expected '{expected}', got {token}")
        self.pos += 1
        return token

    # -------------------------
    # Top-level parser
    # -------------------------
    def parse(self):
        items = []
        while self.peek()[0] != "EOF":
            if self.peek()[1] == "class":
                items.append(self.parse_class())
            elif self.peek()[1] == "module":
                items.append(self.parse_module())
            else:
                # Ignore other top-level constructs
                self.pos += 1
        return {"type": "source", "items": items}

    # -------------------------
    # class my_class; ... endclass
    # -------------------------
    def parse_class(self):
        self.eat("class")
        name = self.eat()[1]

        body = []
        current_text = []

        while not (self.peek()[1] == "endclass"):
            current_text.append(self.eat()[1])

        self.eat("endclass")

        return {
            "type": "class",
            "name": name,
            "body_raw": " ".join(current_text)
        }

    # -------------------------
    # module top(...ports...) ; ... endmodule
    # -------------------------
    def parse_module(self):
        self.eat("module")
        name = self.eat()[1]

        ports = []
        if self.peek()[1] == "(":
            self.eat("(")
            while self.peek()[1] != ")":
                tok = self.eat()[1]
                if tok not in [","]:
                    ports.append(tok)
            self.eat(")")

        # eat semicolon if present
        if self.peek()[1] == ";":
            self.eat(";")

        body = []
        current_text = []
        while not (self.peek()[1] == "endmodule"):
            current_text.append(self.eat()[1])

        self.eat("endmodule")

        return {
            "type": "module",
            "name": name,
            "ports": ports,
            "body_raw": " ".join(current_text)
        }


# -------------------------------------------------------------------
# Top-level function
# -------------------------------------------------------------------

def extract_ast(in_file, out_file):
    with open(in_file, "r") as f:
        code = f.read()

    parser = SVParser(code)
    ast = parser.parse()

    with open(out_file, "w") as f:
        json.dump(ast, f, indent=2)

    print(f"AST written to {out_file}")


# -------------------------------------------------------------------
# Command Line Interface
# -------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sv_ast_dump.py input.sv output.json")
        sys.exit(1)

    extract_ast(sys.argv[1], sys.argv[2])
