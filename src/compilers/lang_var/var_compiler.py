from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    vars = var_tychecker.tycheckModule(m)
    wasm_instrs = compileStmts(m.stmts, vars)

    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]

    module = WasmModule(wasmImports(cfg.maxMemSize),
                        [WasmExport('main', WasmExportFunc(WasmId('$main')))],
                        [],
                        [],
                        WasmFuncTable([]),
                        [WasmFunc(WasmId('$main'), [], None, locals, wasm_instrs)])
    return module

def compileStmts(stmts: list[stmt], vars: set[ident]) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case Assign():
                wasm_instrs.extend(compileAssignStmt(stmt, vars))
            case StmtExp():
                wasm_instrs.extend(compileExpStmt(stmt, vars))
    return wasm_instrs

def compileAssignStmt(stmt: Assign, vars: set[ident]) -> list[WasmInstr]:
    var_tychecker.tycheckStmt(stmt, vars)

    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.right, vars))
    wasm_instrs.append(WasmInstrVarLocal('set', identToWasmId(stmt.var)))
    vars.add(stmt.var)

    return wasm_instrs

def compileExpStmt(stmt: StmtExp, vars: set[ident]) -> list[WasmInstr]:
    var_tychecker.tycheckStmt(stmt, vars)
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.exp, vars))
    return wasm_instrs

def compileExp(e: exp, vars: set[ident]) -> list[WasmInstr]:
    var_tychecker.tycheckExp(e, vars)
    wasm_instrs: list[WasmInstr] = []
    
    match e:
        case IntConst(v):
            wasm_instrs.append(WasmInstrConst('i64', v))
        case Call(id, args):
            var_tychecker.tycheckFuncall(id, args, vars)
            for arg in args:
                wasm_instrs.extend(compileExp(arg, vars))
            wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_i64')))
        case UnOp(USub(), sub):
            wasm_instrs.extend(compileExp(sub, vars))
            wasm_instrs.append(WasmInstrConst('i64', -1))
            wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
        case BinOp(left, op, right):
            wasm_instrs.extend(compileExp(left, vars))
            wasm_instrs.extend(compileExp(right, vars))
            match op:
                case Add():
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'add'))
                case Sub():
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'sub'))
                case Mul():
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
            
        case Name(ident):
            wasm_instrs.append(WasmInstrVarLocal('get', identToWasmId(ident)))

    return wasm_instrs

def identToWasmId(identifier: ident) -> WasmId:
    return WasmId('$' + identifier.name)