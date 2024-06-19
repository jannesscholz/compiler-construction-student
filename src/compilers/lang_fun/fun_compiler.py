from lang_fun.fun_astAtom import *
import lang_fun.fun_ast as PlainAst
from common.wasm import *
import lang_fun.fun_tychecker as fun_tychecker
import compilers.lang_fun.fun_transform as fun_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *

def compileModule(m: PlainAst.mod, cfg: CompilerConfig) -> WasmModule:
    vars = fun_tychecker.tycheckModule(m)
    locals_fun: list[WasmId] = [WasmId('$%'+k.name) for k in vars.funLocals.keys()]
    table = WasmFuncTable(locals_fun)
    fun_intrs = compileFunDefs(m.funs, cfg, table, vars.funLocals)
    la_funs, ctx = fun_transform.transStmts(m.stmts, fun_transform.Ctx())
    wasm_instrs = compileStmts(la_funs, cfg, table)
    locals_temp: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(k), 'i64' if type(v)==Int else 'i32') for k, v in ctx.freshVars.items()]
    locals_var: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x.name), 'i64' if type(x.ty)==Int else 'i32') for x in vars.toplevelLocals]
    module = WasmModule(wasmImports(cfg.maxMemSize),
                        [WasmExport('main', WasmExportFunc(WasmId('$main')))],
                        Globals.decls(),
                        [WasmData(start=1, content="True"), WasmData(start=0, content="False")] + Errors.data(),
                        table,
                        [WasmFunc(WasmId('$main'), [], None, locals_temp + locals_var + Locals.decls(), wasm_instrs)] + fun_intrs)
    return module

def compileFunDefs(funs: list[PlainAst.fun], cfg: CompilerConfig, table: WasmFuncTable, funLocals: dict[ident, list[fun_tychecker.LocalVar]]) -> list[WasmFunc]:
    wasm_instrs: list[WasmFunc] = []
    for fun in funs:
        match fun.result:
            case Void():
                res_ty = None
            case NotVoid(ty):
                res_ty = 'i64' if type(ty)==Int else 'i32'
        la_funs, ctx = fun_transform.transStmts(fun.body, fun_transform.Ctx())
        fun_locals_1: list[tuple[WasmId, WasmValtype]] = [(WasmId("$"+id.name), 'i64' if type(ty)==Int else 'i32') for id, ty in ctx.freshVars.items()]
        fun_locals_2: list[tuple[WasmId, WasmValtype]] = [(WasmId("$"+x.name.name), 'i64' if type(x.ty)==Int else 'i32') for x in funLocals[fun.name]]
        func_instrs = WasmInstrBlock(WasmId("$fun_exit"), res_ty, compileStmts(la_funs, cfg, table) + [WasmInstrConst(res_ty if res_ty is not None else 'i32', 0)])
        wasm_instrs.append(WasmFunc(WasmId('$%'+fun.name.name), [(identToWasmId(x.var), 'i64' if type(x.ty)==Int else 'i32') for x in fun.params], res_ty, fun_locals_1 + fun_locals_2 + Locals.decls(), [func_instrs]))
    return wasm_instrs

def compileStmts(stmts: list[stmt], cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    for stmt in stmts:
        match stmt:
            case Assign():
                wasm_instrs.extend(compileAssignStmt(stmt, cfg, table))
            case StmtExp():
                wasm_instrs.extend(compileExpStmt(stmt, cfg, table))
            case IfStmt():
                wasm_instrs.extend(compileIfStmt(stmt, cfg, table))
            case WhileStmt():
                wasm_instrs.extend(compileWhileStmt(stmt, cfg, table))
            case SubscriptAssign():
                wasm_instrs.extend(compileSubscriptAssignStmt(stmt, cfg, table))
            case Return(result):
                if result is not None and not isinstance(result.ty, Void):
                    wasm_instrs.extend(compileExp(result, cfg, table))
                    wasm_instrs.append(WasmInstrBranch(WasmId("$fun_exit"), False))                
    return wasm_instrs

def compileSubscriptAssignStmt(stmt: SubscriptAssign, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(arrayOffsetInstrs(stmt.left, stmt.index, cfg, table))
    wasm_instrs.extend(compileExp(stmt.right, cfg, table))
    if type(stmt.right) == AtomExp:
        wasm_instrs.append(WasmInstrMem('i64', 'store'))
    else:
        wasm_instrs.append(WasmInstrMem('i32', 'store'))
    return wasm_instrs

def compileIfStmt(stmt: IfStmt, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.cond, cfg, table))
    else_stmts = compileStmts(stmt.elseBody, cfg, table)
    then_stmts = compileStmts(stmt.thenBody, cfg, table)
    wasm_instrs.append(WasmInstrIf(None, then_stmts, else_stmts))
    return wasm_instrs

def compileWhileStmt(stmt: WhileStmt, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    loop_label_start = WasmId('$loop_start')
    loop_label_exit = WasmId('$loop_exit')
    wasm_instrs.append(WasmInstrBlock(loop_label_exit, None, [
        WasmInstrLoop(loop_label_start, compileExp(stmt.cond, cfg, table) + 
            [WasmInstrIf('i32',
                        compileStmts(stmt.body, cfg, table) + [WasmInstrBranch(loop_label_start, conditional=False)],
                        [WasmInstrBranch(loop_label_exit, conditional=False)])
                        ] + [WasmInstrDrop()])
    ]))
    return wasm_instrs

def compileAssignStmt(stmt: Assign, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.right, cfg, table))
    wasm_instrs.append(WasmInstrVarLocal('set', identToWasmId(stmt.var)))
    return wasm_instrs

def compileExpStmt(stmt: StmtExp, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(stmt.exp, cfg, table))
    return wasm_instrs

def tyOfExp(e: exp)-> ty:
    match e.ty:
        case Void():
            raise ValueError()
        case NotVoid(rty):
            match rty:
                case Array():
                    return rty.elemTy
                case _:
                    return rty

def compileExp(e: exp | AtomExp, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    match e:
        case ArrayInitDyn():
            element_size = 8 if isinstance(tyOfExp(e), Int) else 4
            wasm_instrs.extend(compileInitArray(e.len, tyOfExp(e), cfg, table))
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
                                                 + compileExp(AtomExp(e.elemInit, e.ty), cfg, table)
                                                 + [store_command]
                                                 + [WasmInstrVarLocal('get', WasmId('$@tmp_i32')),
                                                    WasmInstrConst('i32', element_size), WasmInstrNumBinOp('i32', 'add'),
                                                    WasmInstrVarLocal('set', WasmId('$@tmp_i32')), WasmInstrBranch(loop_label_start, conditional=False)]
                                                 )
            ]))
        case ArrayInitStatic():
            element_size = 8 if isinstance(tyOfExp(e), Int) else 4
            wasm_instrs.extend(compileInitArray(IntConst(len(e.elemInit), Int()), tyOfExp(e), cfg, table))
            wasm_instrs.append(WasmInstrVarLocal('tee', WasmId('$@tmp_i32')))
            for index, elem in enumerate(e.elemInit):
                wasm_instrs.append(WasmInstrVarLocal('get', WasmId('$@tmp_i32')))
                offset = 4 + index * element_size
                wasm_instrs.append(WasmInstrConst('i32', offset))
                wasm_instrs.append(WasmInstrNumBinOp('i32', 'add'))
                wasm_instrs.extend(compileExp(AtomExp(elem, NotVoid(elem.ty)), cfg, table))
                if element_size == 8:
                    wasm_instrs.append(WasmInstrMem('i64', 'store'))
                else:
                    wasm_instrs.append(WasmInstrMem('i32', 'store'))
        case Subscript(array, index):
            wasm_instrs.extend(arrayOffsetInstrs(array, index, cfg, table))
            match e.ty:
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
                case VarName(ident):
                    wasm_instrs.append(WasmInstrVarLocal('get', identToWasmId(ident)))
                case FunName(fun):
                    if "tmp" in fun.name:
                        wasm_instrs.append(WasmInstrVarLocal('get', identToWasmId(fun)))
                    else:
                        wasm_instrs.append(WasmInstrConst('i32', table.get_index_of_func(WasmId("$%" + fun.name))))
        case Call(id, args):
            for arg in args:
                wasm_instrs.extend(compileExp(arg, cfg, table))
            match id:
                case CallTargetBuiltin(var):
                    if "print" in var.name:
                        match tyOfExp(args[0]):
                            case Array():
                                pass
                            case Bool():
                                wasm_instrs.append(WasmInstrCall(WasmId(f'${var.name.split("_")[0]}_bool')))
                            case Int():
                                wasm_instrs.append(WasmInstrCall(WasmId(f'${var.name.split("_")[0]}_i64')))
                            case Fun():
                                pass
                    elif "input" in var.name:
                        wasm_instrs.append(WasmInstrCall(WasmId(f'${var.name.split("_")[0]}_i64')))
                    elif "len" in var.name:
                        wasm_instrs.extend(arrayLenInstrs())
                case CallTargetDirect(var):
                    wasm_instrs.append(WasmInstrCall(WasmId(f'$%{var.name}')))
                case CallTargetIndirect(var, params, result):
                    wasm_instrs.append(WasmInstrVarLocal('get', identToWasmId(var)))
                    match result:
                        case NotVoid(ty):
                            wasm_instrs.append(WasmInstrCallIndirect(['i64' if type(p)==Int else 'i32' for p in params], 'i64' if type(ty)==Int else 'i32'))
                        case _:
                            pass
        case UnOp(op, sub):
            wasm_instrs.extend(compileExp(sub, cfg, table))
            match op:
                case USub():
                    wasm_instrs.append(WasmInstrConst('i64', -1))
                    wasm_instrs.append(WasmInstrNumBinOp('i64', 'mul'))
                case Not():
                    wasm_instrs.append(WasmInstrConst('i32', 1))
                    wasm_instrs.append(WasmInstrNumBinOp('i32', 'sub'))
        case BinOp(left, op, right):
            if op != And() and op != Or():
                wasm_instrs.extend(compileExp(left, cfg, table))
                wasm_instrs.extend(compileExp(right, cfg, table))
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
                            case Fun():
                                pass
                    case NotEq():
                        match tyOfExp(left):
                            case Array():
                                pass
                            case Bool():
                                wasm_instrs.append(WasmInstrIntRelOp('i32', 'ne'))
                            case Int():
                                wasm_instrs.append(WasmInstrIntRelOp('i64', 'ne'))
                            case Fun():
                                pass
                    case _:
                        pass
            else:
                wasm_instrs.extend(compileExp(left, cfg, table))
                match op:
                    case And():
                        wasm_instrs.append(WasmInstrIf('i32', compileExp(right, cfg, table), [WasmInstrConst('i32', 0)]))
                    case Or():
                        wasm_instrs.append(WasmInstrIf('i32', [WasmInstrConst('i32', 1)], compileExp(right, cfg, table)))
                    case _:
                        pass
    return wasm_instrs

def identToWasmId(identifier: ident) -> WasmId:
    return WasmId('$' + identifier.name)

def compileInitArray(lenExp: atomExp, elemTy: ty, cfg: CompilerConfig, table: WasmFuncTable)-> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(computeLength(lenExp, cfg, table))
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
    wasm_instrs.extend(computeLength(lenExp, cfg, table))
    wasm_instrs.append(WasmInstrConst('i64', 0))
    wasm_instrs.append(WasmInstrIntRelOp('i64', 'lt_s'))
    wasm_instrs.append(WasmInstrIf('i32',
                                   Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],
                                   [WasmInstrConst('i32', 0)]))
    wasm_instrs.append(WasmInstrDrop())
    wasm_instrs.append(WasmInstrVarGlobal('get', Globals.freePtr))
    wasm_instrs.extend(computeLength(lenExp, cfg, table))
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    wasm_instrs.append(WasmInstrConst('i32', 4))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'shl'))
    wasm_instrs.append(WasmInstrConst('i32', 1))
    wasm_instrs.append(WasmInstrNumBinOp('i32', 'xor'))
    wasm_instrs.append(WasmInstrMem('i32', 'store'))
    wasm_instrs.append(WasmInstrVarGlobal('get', Globals.freePtr))
    wasm_instrs.extend(computeLength(lenExp, cfg, table))
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

def arrayOffsetInstrs(arrayExp: atomExp, indexExp: atomExp, cfg: CompilerConfig, table: WasmFuncTable)-> list[WasmInstr]:
    wasm_instrs: list[WasmInstr] = []
    wasm_instrs.extend(compileExp(AtomExp(arrayExp, NotVoid(arrayExp.ty)), cfg, table))
    wasm_instrs.extend(arrayLenInstrs())
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    wasm_instrs.extend(compileExp(AtomExp(indexExp, NotVoid(indexExp.ty)), cfg, table))
    wasm_instrs.append(WasmInstrConvOp('i32.wrap_i64'))
    wasm_instrs.append(WasmInstrIntRelOp('i32', 'le_u'))
    wasm_instrs.append(WasmInstrIf('i32', 
                                   Errors.outputError(Errors.arrayIndexOutOfBounds) + [WasmInstrTrap()],
                                   [WasmInstrConst('i32', 0)]))
    wasm_instrs.append(WasmInstrDrop())
    wasm_instrs.extend(compileExp(AtomExp(arrayExp, NotVoid(arrayExp.ty)), cfg, table))
    wasm_instrs.extend(compileExp(AtomExp(indexExp, NotVoid(indexExp.ty)), cfg, table))
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

def computeLength(lenExp: atomExp, cfg: CompilerConfig, table: WasmFuncTable) -> list[WasmInstr]:
    return compileExp(AtomExp(lenExp, NotVoid(lenExp.ty)), cfg, table)