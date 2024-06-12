import assembly.tacSpill_ast as tacSpill
import assembly.mips_ast as mips
from typing import *
from assembly.common import *
from assembly.mipsHelper import *
from common.compilerSupport import *

def assignToMips(i: tacSpill.Assign) -> list[mips.instr]:
    r: list[mips.instr] = []
    match i.left:
        case tacSpill.BinOp(tacSpill.Name(x), tacSpill.Op("ADD"), tacSpill.Name(y)):
            r.append(mips.Op(mips.Add(), mips.Reg(i.var.name), mips.Reg(x.name), mips.Reg(y.name)))
        case tacSpill.BinOp(tacSpill.Const(x), tacSpill.Op("ADD"), tacSpill.Name(y)):
            r.append(mips.OpI(mips.AddI(), mips.Reg(i.var.name), mips.Reg(y.name), mips.Imm(x)))
        case tacSpill.BinOp(tacSpill.Name(x), tacSpill.Op("ADD"), tacSpill.Const(y)):
            r.append(mips.OpI(mips.AddI(), mips.Reg(i.var.name), mips.Reg(x.name), mips.Imm(y)))
        case tacSpill.BinOp(tacSpill.Const(x), tacSpill.Op("ADD"), tacSpill.Const(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(x)))
            r.append(mips.OpI(mips.AddI(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Imm(y)))

        case tacSpill.BinOp(tacSpill.Name(x), tacSpill.Op("SUB"), tacSpill.Name(y)):
            r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg(x.name), mips.Reg(y.name)))
        case tacSpill.BinOp(tacSpill.Const(x), tacSpill.Op("SUB"), tacSpill.Name(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(x)))
            r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg(y.name)))
        case tacSpill.BinOp(tacSpill.Name(x), tacSpill.Op("SUB"), tacSpill.Const(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(y)))
            r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg(x.name), mips.Reg('$t2')))
        case tacSpill.BinOp(tacSpill.Const(x), tacSpill.Op("SUB"), tacSpill.Const(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(x)))
            r.append(mips.LoadI(mips.Reg('$t3'), mips.Imm(y)))
            r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg('$t3')))

        case tacSpill.BinOp(tacSpill.Name(x), tacSpill.Op("MUL"), tacSpill.Name(y)):
            r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg(x.name), mips.Reg(y.name)))
        case tacSpill.BinOp(tacSpill.Const(x), tacSpill.Op("MUL"), tacSpill.Name(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(x)))
            r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg(y.name)))
        case tacSpill.BinOp(tacSpill.Name(x), tacSpill.Op("MUL"), tacSpill.Const(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(y)))
            r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg(x.name), mips.Reg('$t2')))
        case tacSpill.BinOp(tacSpill.Const(x), tacSpill.Op("MUL"), tacSpill.Const(y)):
            r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(x)))
            r.append(mips.LoadI(mips.Reg('$t3'), mips.Imm(y)))
            r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg('$t3')))

        case tacSpill.Prim(tacSpill.Const(v)):
            r.append(mips.LoadI(mips.Reg(i.var.name), mips.Imm(v)))

        case tacSpill.Prim(tacSpill.Name(v)):
            if i.var == v:
                r.append(mips.Move(mips.Reg('$t2'), mips.Reg(v.name)))
                r.append(mips.Move(mips.Reg(i.var.name), mips.Reg('$t2')))
            else:
                r.append(mips.Move(mips.Reg(i.var.name), mips.Reg(v.name)))
        case _:
            print(f"{i} is not handled.")
    return r
