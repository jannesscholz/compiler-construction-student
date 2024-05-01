from lark import ParseTree
from lang_var.var_ast import *
from parsers.common import *
import common.log as log

grammarFile = "./src/parsers/lang_var/var_grammar.lark"

def parse(args: ParserArgs) -> exp:
    print(args)
    parseTree = parseAsTree(args, grammarFile, 'lvar')
    ast = parseTreeToExpAst(parseTree)
    log.debug(f'AST: {ast}')
    return ast

def parseTreeToExpAst(t: ParseTree) -> exp:
    match t.data:
        case 'var_exp':
            b: Any[Token | Tree[Token]] = t.children[0]
            a: Any = b.value
            return Name(Ident(a))
        case 'exp_int':
            return IntConst(int(asToken(t.children[0])))
        case 'exp_add':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Add(), parseTreeToExpAst(e2))
        case 'exp_sub':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Sub(), parseTreeToExpAst(e2))
        case 'exp_mul':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Mul(), parseTreeToExpAst(e2))
        case 'exp':
            b: Any[Token | Tree[Token]] = t.children[0]
            return parseTreeToExpAst(b)
        case 'function_call_all':
            b: Any[Token | Tree[Token]] = t.children[0]
            q: Any[Token | Tree[Token]] = t.children[1:]
            l = [parseTreeToExpAst(x) for x in q]
            return Call(Ident(b.value), l)
        case 'exp_neg':
            b: Any[Token | Tree[Token]] = t.children[0]
            return UnOp(USub(), parseTreeToExpAst(b))
        case 'exp_1' | 'exp_2' | 'exp_paren':
            return parseTreeToExpAst(asTree(t.children[0]))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for exp: {t}')

def parseModule(args: ParserArgs) -> mod:
    parseTree = parseAsTree(args, grammarFile, 'lvar')
    ast = parseTreeToModuleAst(parseTree)
    log.debug(f'Module AST: {ast}')
    return ast

def parseTreeToStmtAst(t: ParseTree) -> stmt: # fix
    match t.data:
        case 'var_assign_stmt':
            b: Any[Token | Tree[Token]] = t.children[0]
            return Assign(Ident(b.children[0].value), parseTreeToExpAst(asTree(t.children[1])))
        case 'exp_stmt':
            return StmtExp(parseTreeToExpAst(asTree(t.children[0])))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for stmt: {t}')

def parseTreeToStmtListAst(t: ParseTree)-> list[stmt]: # fix
    stmt_list: list[stmt] = []
    for child in t.children:
        stmt_list.append(parseTreeToStmtAst(asTree(child)))
    return stmt_list

def parseTreeToModuleAst(t: ParseTree)-> mod: # fix
    stmt_list = parseTreeToStmtListAst(asTree(t))
    return Module(stmt_list)