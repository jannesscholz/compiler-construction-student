from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    vars = loop_tychecker.tycheckModule(m)
    wasm_instrs = compileStmts(m.stmts)
    #print(wasm_instrs)
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64' if type(y)==Int else 'i32') for x, y in vars.types()]

    module = WasmModule(wasmImports(cfg.maxMemSize),
                        [WasmExport('main', WasmExportFunc(WasmId('$main')))],
                        [],
                        [],
                        WasmFuncTable([]),
                        [WasmFunc(WasmId('$main'), [], None, locals, wasm_instrs)])
    
    return module

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case Assign():
                wasm_instrs.extend(compileAssignStmt(stmt))
            case StmtExp():
                wasm_instrs.extend(compileExpStmt(stmt))
            case IfStmt():
                wasm_instrs.extend(compileIfStmt(stmt))
            case WhileStmt():
                wasm_instrs.extend(compileWhileStmt(stmt))
    return wasm_instrs

def compileIfStmt(stmt: IfStmt) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    
    wasm_instrs.extend(compileExp(stmt.cond))
    wasm_instrs.extend([WasmInstrIf('i32', compileStmts(stmt.thenBody) + [WasmInstrConst('i32', 0)], compileStmts(stmt.elseBody) + [WasmInstrConst('i32', 0)])] + [WasmInstrDrop()])

    return wasm_instrs

def compileWhileStmt(stmt: WhileStmt) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []

    return wasm_instrs

def compileAssignStmt(stmt: Assign) -> list[WasmInstr]:

    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.right))
    wasm_instrs.append(WasmInstrVarLocal('set', identToWasmId(stmt.var)))

    return wasm_instrs

def compileExpStmt(stmt: StmtExp) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.exp))
    return wasm_instrs

def tyOfExp(e: exp)-> ty:
    match e.ty:
        case None:
            raise ValueError()
        case Void():
            raise ValueError()
        case NotVoid(rty):
            return rty

def compileExp(e: exp) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    
    match e:
        case BoolConst(v):
            match v:
                case True:
                    wasm_instrs.append(WasmInstrConst('i32', 1))
                case False:
                    wasm_instrs.append(WasmInstrConst('i32', 0))
        case IntConst(v):
            wasm_instrs.append(WasmInstrConst('i64', v))
        case Call(id, args):
            for arg in args:
                wasm_instrs.extend(compileExp(arg))
            if "print" in id.name:
                match tyOfExp(args[0]):
                    case Bool():
                        wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_i32')))
                    case Int():
                        wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_i64')))
            elif "input" in id.name:
                wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_i64')))
        case UnOp(op, sub):
            match op:
                case USub():
                    wasm_instrs.extend(compileExp(sub))
                    wasm_instrs.append(WasmInstrConst('i64', -1))
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
                case Not():
                    wasm_instrs.extend(compileExp(sub))
                    wasm_instrs.append(WasmInstrConst('i32', 1))
                    wasm_instrs.append(WasmInstrNumBinOp('i32', 'sub'))
        case BinOp(left, op, right):
            match op:
                case Add():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'add'))
                case Sub():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'sub'))
                case Mul():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
                case LessEq():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrIntRelOp('i64', 'le_s'))
                case Less():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrIntRelOp('i64', 'lt_s'))
                case Greater():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrIntRelOp('i64', 'gt_s'))
                case GreaterEq():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    wasm_instrs.append(WasmInstrIntRelOp('i64', 'ge_s'))
                case Eq():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    match tyOfExp(left):
                        case Bool():
                            wasm_instrs.append(WasmInstrIntRelOp('i32', 'eq'))
                        case Int():
                            wasm_instrs.append(WasmInstrIntRelOp('i64', 'eq'))
                case NotEq():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.extend(compileExp(right))
                    match tyOfExp(left):
                        case Bool():
                            wasm_instrs.append(WasmInstrIntRelOp('i32', 'ne'))
                        case Int():
                            wasm_instrs.append(WasmInstrIntRelOp('i64', 'ne'))
                case And():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.append(WasmInstrIf('i32', compileExp(right), [WasmInstrConst('i32', 0)]))
                case Or():
                    wasm_instrs.extend(compileExp(left))
                    wasm_instrs.append(WasmInstrIf('i32', [WasmInstrConst('i32', 1)], compileExp(right)))
                
            
        case Name(ident):
            wasm_instrs.append(WasmInstrVarLocal('get', identToWasmId(ident)))

    return wasm_instrs

def identToWasmId(identifier: ident) -> WasmId:
    return WasmId('$' + identifier.name)