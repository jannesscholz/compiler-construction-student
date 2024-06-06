"""
A pretty printer for TAC.
"""
from assembly.tac_ast import *

def prettyPrim(p: prim) -> str:
    match p:
        case Const(v): return str(v)
        case Name(Ident(x)): return x

def prettyExp(e: exp) -> str:
    match e:
        case Prim(p): return prettyPrim(p)
        case BinOp(l, Op(op), r):
            return f'{op}({prettyPrim(l)}, {prettyPrim(r)})'

def prettyInstr(instr: instr) -> str:
    match instr:
        case Assign(x, e):
            return f'  {x.name} = {prettyExp(e)}'
        case Call(x, fun, args):
            prettyArgs = [prettyPrim(a) for a in args]
            if args:
                argStr = ', '.join(prettyArgs)
                callStr = f'CALL({fun.name}, {argStr})'
            else:
                callStr = f'CALL({fun.name})'
            match x:
                case None:
                    return f'  {callStr}'
                case _:
                    return f'  {x.name} = {callStr}'
        case GotoIf(test, label):
            return f'  IF {prettyPrim(test)} GOTO {label}'
        case Goto(label):
            return f'  GOTO {label}'
        case Label(label):
            return f'{label}:'

def prettyInstrs(l: list[instr], oneLine: bool=False) -> str:
    out = [prettyInstr(i) for i in l]
    if oneLine:
        return ';'.join([x.strip() for x in out])
    else:
        return '\n'.join(out)
