BRACKETS = {
    "(": ")",
    "[": "]",
    "{": "}",
    "<": ">"
}


class Builtins:
    class OperationCallbacks:
        @classmethod
        def all(cls):
            return {
                "+": cls.add,
                "-": cls.subtract,
                "*": cls.multiply,
                "/": cls.divide,
                "//": cls.floordiv,
                "%": cls.modulo,
                "^": cls.exponent
            }

        @staticmethod
        def add(first, second):
            return first + second

        @staticmethod
        def subtract(first, second):
            return first - second

        @staticmethod
        def multiply(first, second):
            return first * second

        @staticmethod
        def divide(first, second):
            return first / second

        @staticmethod
        def floordiv(first, second):
            return first // second

        @staticmethod
        def modulo(first, second):
            return first % second

        @staticmethod
        def exponent(first, second):
            return first ** second


class Token:
    def __init__(self, raw: str, parent_expression: str):
        self.raw = raw
        self.parent_expression = parent_expression

    def __repr__(self):
        return f'Token({self.raw})'


class Number(Token):
    def __init__(self, value, *args):
        super().__init__(*args)
        self.value = value

    def __repr__(self):
        return f'Token:Number({self.value})'


class Variable(Token):
    def __init__(self, name, assigned_to=None, *args):
        super().__init__(*args)
        self.name = name
        self.value = assigned_to

    def __repr__(self):
        return (
            f'Token:Variable({self.name})'
            if not self.value else f'Token:Variable({self.name}={self.value})'
        )


class Term(Token):
    def __init__(self, coefficient: Number = Number(1, None, None), variable: Variable = None, exponent: Number = Number(1, None, None), *args):
        super().__init__(*args)
        self.coefficient = coefficient
        self.variable = variable
        self.exponent = exponent

    def __repr__(self):
        return f'Token:Term({self!s})'

    def __str__(self):
        return f'{self.coefficient.value}{self.variable.name}^{self.exponent.value}'

    @property
    def value(self):
        return (
            self.coefficient.value ** self.exponent.value
            if not self.variable or not self.variable.value
            else self.coefficient.value * self.variable.value ** self.exponent.value
        )


class Operation(Token):
    def __init__(self, operation, *args):
        super().__init__(*args)
        self.operation = operation
        self.callback = Builtins.OperationCallbacks.all().get(operation, None)

    def __repr__(self):
        return f'Token:Operation({self.operation})'


class Expression:
    def __init__(self, tokens):
        self.tokens = tokens

    def __repr__(self):
        return f"Expression::{len(self.tokens)}({', '.join(f'{_!r}' for _ in self.tokens)})"


def to_expression(expression: str):
    tokens = []
    buffer = ""
    in_bracket = False
    end_bracket = None
    expression = expression.replace(' ', '')
    expression = expression.replace('\n', ';')
    for pointer, char in enumerate(expression):
        if in_bracket:
            if char == end_bracket and expression[pointer - 1] != "\\":
                tokens.append(to_expression(buffer))
                in_bracket = False
                end_bracket = None
                buffer = ''
                continue
        else:
            if char in BRACKETS.keys() and expression[pointer - 1] != "\\":
                in_bracket = True
                end_bracket = BRACKETS[char]
                continue
            if char in Builtins.OperationCallbacks.all() and char != "-":
                tokens.append(Number(float(buffer), buffer, expression))  # Should be term
                tokens.append(Operation(char, char, expression))
                buffer = ''

            future = buffer + char
            if char == "-" and not future.startswith("-"):
                tokens.append(Operation(char, char, expression))

        buffer += char
    return Expression(tokens)


class Parser:
    def __init__(self, expression: str):
        self.expression = expression
        self.variables = {}
        self.functions = {}
        self.chunks = []
        self.unknowns = []


    def parse(self):
        return to_expression(self.expression)
