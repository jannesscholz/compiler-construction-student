from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *
#import common.utils as utils

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    var_tychecker.tycheckModule(m)
    wasm_instrs = compileStmts(m.stmts)
    wasm_instrs: list[WasmInstr] = [WasmInstrConst('i64', 1), WasmInstrCall(WasmId('$print_i64'))]
    main = WasmFunc(WasmId('$main'), [], None, [], wasm_instrs)
    module = WasmModule(wasmImports(cfg.maxMemSize), [WasmExport('main', WasmExportFunc(WasmId('$main')))], [], [], WasmFuncTable([]), [main])
    print(module)
    return module

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []

    for stmt in stmts:
        match stmt:
            case Assign():
                wasm_instrs.extend(compileAssignStmt(stmt))
            case StmtExp():
                wasm_instrs.extend(compileExpStmt(stmt))
    return wasm_instrs

def compileAssignStmt(stmt: Assign) -> list[WasmInstr]:
    var_tychecker.tycheckStmt(stmt, set())

    #stmt.var
    #WasmInstr

    wasm_instrs = []
    wasm_instrs.extend(compileIdent(stmt.var))
    return wasm_instrs

def compileIdent(var: ident) -> list[WasmInstr]:
    wasm_instrs = []
    return wasm_instrs

def compileExpStmt(stmt: StmtExp) -> list[WasmInstr]:
    var_tychecker.tycheckStmt(stmt, set())
    wasm_instrs = []
    
    return wasm_instrs