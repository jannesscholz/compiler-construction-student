from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    str_token = toks.ensureNext("STRING")
    toks.ensureNext("COLON")
    json_token = ruleJson(toks)
    return (str_token.value[1:-1], json_token)
    
        
def ruleString(toks: TokenStream) -> str:
    return toks.ensureNext("STRING").value[1:-1]

def ruleInt(toks: TokenStream) -> int:
    return int(toks.ensureNext("INT").value)

def ruleJson(toks: TokenStream) -> Json:
    """
    Parses a JSON object, a JSON string, or a JSON number.
    """
    if toks.lookahead().type == "STRING":
        return ruleString(toks)
    elif toks.lookahead().type == "INT":
        return ruleInt(toks)
    elif toks.lookahead().type == "LBRACE":
        return ruleEntryList(toks)
    else:
        raise SyntaxError("Expected string, integer, or object")

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    """
    Parses the content of a JSON object.
    """
    obj: dict[str, Json] = {}
    if toks.lookahead().type == "LBRACE":
        toks.ensureNext("LBRACE")
        while toks.lookahead().type != "RBRACE":
            key, value = ruleEntry(toks)
            obj[key] = value
            if toks.lookahead().type == "COMMA":
                toks.ensureNext("COMMA")
        toks.ensureNext("RBRACE")
    return obj

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res