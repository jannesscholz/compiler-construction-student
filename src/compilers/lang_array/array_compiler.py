from lang_array.array_astAtom import *
import lang_array.array_ast as PlainAst
from common.wasm import *
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *

def compileModule(m: PlainAst.mod, cfg: CompilerConfig) -> WasmModule:
    vars = array_tychecker.tycheckModule(m)
    la_array, ctx = array_transform.transStmts(m.stmts, array_transform.Ctx())
    wasm_instrs = compileStmts(la_array, cfg)
    locals_temp: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(k), 'i64' if type(v)==Int else 'i32') for k, v in ctx.freshVars.items()]
    locals_var: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64' if type(y)==Int else 'i32') for x, y in vars.types()]
    module = WasmModule(wasmImports(cfg.maxMemSize),
                        [WasmExport('main', WasmExportFunc(WasmId('$main')))],
                        Globals.decls(),
                        [WasmData(start=1, content="True"), WasmData(start=0, content="False")] + Errors.data(),
                        WasmFuncTable([]),
                        [WasmFunc(WasmId('$main'), [], None, locals_temp + locals_var + Locals.decls(), wasm_instrs)])
    return module

def compileStmts(stmts: list[stmt], cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    for stmt in stmts:
        match stmt:
            case Assign():
                wasm_instrs.extend(compileAssignStmt(stmt, cfg))
            case StmtExp():
                wasm_instrs.extend(compileExpStmt(stmt, cfg))
            case IfStmt():
                wasm_instrs.extend(compileIfStmt(stmt, cfg))
            case WhileStmt():
                wasm_instrs.extend(compileWhileStmt(stmt, cfg))
            case SubscriptAssign():
                wasm_instrs.extend(compileSubscriptAssignStmt(stmt, cfg))
    return wasm_instrs

def compileSubscriptAssignStmt(stmt: SubscriptAssign, cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(arrayOffsetInstrs(stmt.left, stmt.index, cfg))
    wasm_instrs.extend(compileExp(stmt.right, cfg))
    if type(stmt.right) == AtomExp:
        wasm_instrs.append(WasmInstrMem('i64', 'store'))
    else:
        wasm_instrs.append(WasmInstrMem('i32', 'store'))
    return wasm_instrs

def compileIfStmt(stmt: IfStmt, cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.cond, cfg))
    wasm_instrs.extend([WasmInstrIf('i32', compileStmts(stmt.thenBody, cfg) + [WasmInstrConst('i32', 0)], compileStmts(stmt.elseBody, cfg) + [WasmInstrConst('i32', 0)])] + [WasmInstrDrop()])
    return wasm_instrs

def compileWhileStmt(stmt: WhileStmt, cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    loop_label_start = WasmId('$loop_start')
    loop_label_exit = WasmId('$loop_exit')
    wasm_instrs.append(WasmInstrBlock(loop_label_exit, None, [
        WasmInstrLoop(loop_label_start, compileExp(stmt.cond, cfg) + 
            [WasmInstrIf('i32',
                        compileStmts(stmt.body, cfg) + [WasmInstrBranch(loop_label_start, conditional=False)],
                        [WasmInstrBranch(loop_label_exit, conditional=False)])
                        ] + [WasmInstrDrop()])
    ]))
    return wasm_instrs

def compileAssignStmt(stmt: Assign, cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.right, cfg))
    wasm_instrs.append(WasmInstrVarLocal('set', identToWasmId(stmt.var)))
    return wasm_instrs

def compileExpStmt(stmt: StmtExp, cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.exp, cfg))
    return wasm_instrs

def tyOfExp(e: exp)-> ty:
    match e.ty:
        case None:
            raise ValueError()
        case Void():
            raise ValueError()
        case NotVoid(rty):
            match rty:
                case Array():
                    return rty.elemTy
                case _:
                    return rty

def compileExp(e: exp | AtomExp, cfg: CompilerConfig) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    match e:
        case ArrayInitDyn():
            element_size = 8 if isinstance(tyOfExp(e), Int) else 4
            wasm_instrs.extend(compileInitArray(e.len, tyOfExp(e), cfg))
            wasm_instrs.append(WasmInstrVarLocal('tee', WasmId('$@tmp_i32')))
            wasm_instrs.append(WasmInstrVarLocal('get', WasmId('$@tmp_i32')))
            wasm_instrs.append(WasmInstrConst('i32', 4))
            wasm_instrs.append(WasmInstrNumBinOp('i32', 'add'))
            wasm_instrs.append(WasmInstrVarLocal('set', WasmId('$@tmp_i32')))
            loop_label_start = WasmId('$loop_start')
            loop_label_exit = WasmId('$loop_exit')
            if type(tyOfExp(e)) == Array or type(tyOfExp(e)) == Bool:
                store_command = WasmInstrMem('i32', 'store')
            else:
                store_command = WasmInstrMem('i64', 'store')
            wasm_instrs.append(WasmInstrBlock(loop_label_exit, None, [
                WasmInstrLoop(loop_label_start, [WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                                                 WasmInstrVarGlobal('get', Globals.freePtr),
                                                 WasmInstrIntRelOp('i32', 'lt_u'),
                                                 WasmInstrIf('i32', [WasmInstrConst('i32', 0)], [WasmInstrBranch(loop_label_exit, conditional=False)]),
                                                 WasmInstrDrop(),
                                                 WasmInstrVarLocal('get', WasmId('$@tmp_i32'))]
                                                 + compileExp(AtomExp(e.elemInit), cfg)
                                                 + [store_command]
                                                 + [WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                                                    WasmInstrConst('i32', element_size), WasmInstrNumBinOp('i32', 'add'),
                                                    WasmInstrVarLocal('set', WasmId('$@tmp_i32')), WasmInstrBranch(loop_label_start, conditional=False)]
                                                 )
            ]))
        case ArrayInitStatic():
            element_size = 8 if isinstance(tyOfExp(e), Int) else 4
            wasm_instrs.extend(compileInitArray(IntConst(len(e.elemInit)), tyOfExp(e), cfg))
            wasm_instrs.append(WasmInstrVarLocal('tee', WasmId('$@tmp_i32')))
            for index, elem in enumerate(e.elemInit):
                wasm_instrs.append(WasmInstrVarLocal('get', WasmId('$@tmp_i32')))
                offset = 4 + index * element_size
                wasm_instrs.append(WasmInstrConst('i32', offset))
                wasm_instrs.append(WasmInstrNumBinOp('i32', 'add'))
                wasm_instrs.extend(compileExp(AtomExp(elem), cfg))
                if element_size == 8:
                    wasm_instrs.append(WasmInstrMem('i64', 'store'))
                else:
                    wasm_instrs.append(WasmInstrMem('i32', 'store'))
        case Subscript():
            wasm_instrs.extend(arrayOffsetInstrs(e.array, e.index, cfg))
            match e.ty:
                case None:
                    raise ValueError()
                case Void():
                    raise ValueError()
                case NotVoid(rty):
                    match rty:
                        case Int():
                            wasm_instrs.append(WasmInstrMem('i64', 'load'))
                        case _:
                            wasm_instrs.append(WasmInstrMem('i32', 'load'))
        case AtomExp(x):
            match x:
                case BoolConst(v):
                    match v:
                        case True:
                            wasm_instrs.append(WasmInstrConst('i32', 1))
                        case False:
                            wasm_instrs.append(WasmInstrConst('i32', 0))
                case IntConst(v):
                    wasm_instrs.append(WasmInstrConst('i64', v))
                case Name(ident):
                    wasm_instrs.append(WasmInstrVarLocal('get', identToWasmId(ident)))
        case Call(id, args):
            for arg in args:
                wasm_instrs.extend(compileExp(arg, cfg))
            if "print" in id.name:
                match tyOfExp(args[0]):
                    case Array():
                        pass
                    case Bool():
                        wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_bool')))
                    case Int():
                        wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_i64')))
            elif "input" in id.name:
                wasm_instrs.append(WasmInstrCall(WasmId(f'${id.name.split("_")[0]}_i64')))
            elif "len" in id.name:
                wasm_instrs.extend(arrayLenInstrs())
        case UnOp(op, sub):
            wasm_instrs.extend(compileExp(sub, cfg))
            match op:
                case USub():
                    wasm_instrs.append(WasmInstrConst('i64', -1))
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
                case Not():
                    wasm_instrs.append(WasmInstrConst('i32', 1))
                    wasm_instrs.append(WasmInstrNumBinOp('i32', 'sub'))
        case BinOp(left, op, right):
            if op != And() and op != Or():
                wasm_instrs.extend(compileExp(left, cfg))
                wasm_instrs.extend(compileExp(right, cfg))
                match op:
                    case Is():
                        wasm_instrs.append(WasmInstrIntRelOp('i32', 'eq'))
                    case Add():
                        wasm_instrs.append(WasmInstrNumBinOp('i64', 'add'))
                    case Sub():
                        wasm_instrs.append(WasmInstrNumBinOp('i64', 'sub'))
                    case Mul():
                        wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
                    case LessEq():
                        wasm_instrs.append(WasmInstrIntRelOp('i64', 'le_s'))
                    case Less():
                        wasm_instrs.append(WasmInstrIntRelOp('i64', 'lt_s'))
                    case Greater():
                        wasm_instrs.append(WasmInstrIntRelOp('i64', 'gt_s'))
                    case GreaterEq():
                        wasm_instrs.append(WasmInstrIntRelOp('i64', 'ge_s'))
                    case Eq():
                        match tyOfExp(left):
                            case Array():
                                pass
                            case Bool():
                                wasm_instrs.append(WasmInstrIntRelOp('i32', 'eq'))
                            case Int():
                                wasm_instrs.append(WasmInstrIntRelOp('i64', 'eq'))
                    case NotEq():
                        match tyOfExp(left):
                            case Array():
                                pass
                            case Bool():
                                wasm_instrs.append(WasmInstrIntRelOp('i32', 'ne'))
                            case Int():
                                wasm_instrs.append(WasmInstrIntRelOp('i64', 'ne'))
                    case _:
                        pass
            else:
                wasm_instrs.extend(compileExp(left, cfg))
                match op:
                    case And():
                        wasm_instrs.append(WasmInstrIf('i32', compileExp(right, cfg), [WasmInstrConst('i32', 0)]))
                    case Or():
                        wasm_instrs.append(WasmInstrIf('i32', [WasmInstrConst('i32', 1)], compileExp(right, cfg)))
                    case _:
                        pass
    return wasm_instrs

def identToWasmId(identifier: ident) -> WasmId:
    return WasmId('$' + identifier.name)

def compileInitArray(lenExp: atomExp, elemTy: ty, cfg: CompilerConfig)-> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(computeLength(lenExp, cfg))
    if isinstance(elemTy, Int):
        wasm_instrs.append(WasmInstrConst('i64', 8))
    else:
        wasm_instrs.append(WasmInstrConst('i64', 4))
    wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
    wasm_instrs.append(WasmInstrConst('i64', cfg.maxArraySize))
    wasm_instrs.append(WasmInstrIntRelOp('i64', 'gt_s'))
    wasm_instrs.append(WasmInstrIf('i32',
                                   Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],
                                   [WasmInstrConst('i32', 0)]))
    wasm_instrs.append(WasmInstrDrop())
    wasm_instrs.extend(computeLength(lenExp, cfg))
    wasm_instrs.append(WasmInstrConst('i64', 0))
    wasm_instrs.append(WasmInstrIntRelOp('i64', 'lt_s'))
    wasm_instrs.append(WasmInstrIf('i32',
                                   Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],
                                   [WasmInstrConst('i32', 0)]))
    wasm_instrs.append(WasmInstrDrop())
    wasm_instrs.append(WasmInstrVarGlobal('get', Globals.freePtr))
    wasm_instrs.extend(computeLength(lenExp, cfg))
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    wasm_instrs.append(WasmInstrConst('i32', 4))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'shl'))
    wasm_instrs.append(WasmInstrConst('i32', 1))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'xor'))
    wasm_instrs.append(WasmInstrMem('i32', 'store'))
    wasm_instrs.append(WasmInstrVarGlobal('get', Globals.freePtr))
    wasm_instrs.extend(computeLength(lenExp, cfg))
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    if isinstance(elemTy, Int):
        wasm_instrs.append(WasmInstrConst('i32', 8))
    else:
        wasm_instrs.append(WasmInstrConst('i32', 4))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'mul'))
    wasm_instrs.append(WasmInstrConst('i32', 4))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'add'))
    wasm_instrs.append(WasmInstrVarGlobal('get', Globals.freePtr))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'add'))
    wasm_instrs.append(WasmInstrVarGlobal('set', Globals.freePtr))
    return wasm_instrs

def arrayLenInstrs() -> list[WasmInstr]:
    return [WasmInstrMem('i32', 'load'), WasmInstrConst('i32', 4), WasmInstrNumBinOp('i32', 'shr_u'), WasmInstrConvOp('i64.extend_i32_u')]

def arrayOffsetInstrs(arrayExp: atomExp, indexExp: atomExp, cfg: CompilerConfig)-> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(AtomExp(arrayExp), cfg))
    wasm_instrs.extend(arrayLenInstrs())
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    wasm_instrs.extend(compileExp(AtomExp(indexExp), cfg))
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    wasm_instrs.append(WasmInstrIntRelOp('i32', 'le_u'))
    wasm_instrs.append(WasmInstrIf('i32', 
                                   Errors.outputError(Errors.arrayIndexOutOfBounds) + [WasmInstrTrap()],
                                   [WasmInstrConst('i32', 0)]))
    wasm_instrs.append(WasmInstrDrop())
    wasm_instrs.extend(compileExp(AtomExp(arrayExp), cfg))
    wasm_instrs.extend(compileExp(AtomExp(indexExp), cfg))
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    if isinstance(arrayExp.ty.elemTy, Int): # type: ignore
        wasm_instrs.append(WasmInstrConst('i32', 8))
    else:
        wasm_instrs.append(WasmInstrConst('i32', 4))
    wasm_instrs += [
        WasmInstrNumBinOp('i32', 'mul'),
        WasmInstrConst('i32', 4),
        WasmInstrNumBinOp('i32', 'add'),
        WasmInstrNumBinOp('i32', 'add')
    ]
    return wasm_instrs

def computeLength(lenExp: atomExp, cfg: CompilerConfig) -> list[WasmInstr]:
    return compileExp(AtomExp(lenExp), cfg)