#import assembly.tac_ast as tac
import assembly.tacSpill_ast as tacSpill
import assembly.mips_ast as mips
from typing import *
from assembly.common import *
#import assembly.tacInterp as tacInterp
from assembly.mipsHelper import *
from common.compilerSupport import *

def assignToMips(i: tacSpill.Assign) -> list[mips.instr]:
    r: list[mips.instr] = []
    print("------------------------")
    print(i)
    match i.left:
        case tacSpill.BinOp():
            match i.left.op.name:
                case "ADD":
                    if type(i.left.left) == tacSpill.Name and type(i.left.right) == tacSpill.Name:
                        if i.left.left == i.left.right and i.left.left.var == i.var:
                            # special case in which a test fails
                            r.append(mips.Move(mips.Reg('$t2'), mips.Reg(i.left.left.var.name)))
                            r.append(mips.Move(mips.Reg('$t3'), mips.Reg(i.left.right.var.name)))
                            r.append(mips.Op(mips.Add(), mips.Reg('$t2'), mips.Reg('$t2'), mips.Reg('$t3')))
                            r.append(mips.Move(mips.Reg(i.var.name), mips.Reg('$t2')))
                        else:
                            r.append(mips.Op(mips.Add(), mips.Reg(i.var.name), mips.Reg(i.left.left.var.name), mips.Reg(i.left.right.var.name)))
                    elif type(i.left.left) == tacSpill.Const and type(i.left.right) == tacSpill.Name:
                        r.append(mips.OpI(mips.AddI(), mips.Reg(i.var.name), mips.Reg(i.left.right.var.name), mips.Imm(i.left.left.value)))
                    elif type(i.left.right) == tacSpill.Const and type(i.left.left) == tacSpill.Name:
                        r.append(mips.OpI(mips.AddI(), mips.Reg(i.var.name), mips.Reg(i.left.left.var.name), mips.Imm(i.left.right.value)))
                    elif type(i.left.right) == tacSpill.Const and type(i.left.left) == tacSpill.Const:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.right.value)))
                        r.append(mips.OpI(mips.AddI(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Imm(i.left.left.value)))
                case "SUB":
                    if type(i.left.left) == tacSpill.Name and type(i.left.right) == tacSpill.Name:
                        r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg(i.left.left.var.name), mips.Reg(i.left.right.var.name)))
                    elif type(i.left.left) == tacSpill.Const and type(i.left.right) == tacSpill.Name:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.left.value)))
                        r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg(i.left.right.var.name)))
                    elif type(i.left.right) == tacSpill.Const and type(i.left.left) == tacSpill.Name:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.right.value)))
                        r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg(i.left.left.var.name), mips.Reg('$t2')))
                    elif type(i.left.right) == tacSpill.Const and type(i.left.left) == tacSpill.Const:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.left.value)))
                        r.append(mips.LoadI(mips.Reg('$t3'), mips.Imm(i.left.right.value)))
                        r.append(mips.Op(mips.Sub(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg('$t3')))
                case "MUL":
                    if type(i.left.left) == tacSpill.Name and type(i.left.right) == tacSpill.Name:
                        if i.left.left == i.left.right and i.left.left.var == i.var:
                            # special case in which a test fails
                            r.append(mips.Move(mips.Reg('$t2'), mips.Reg(i.left.left.var.name)))
                            r.append(mips.Move(mips.Reg('$t3'), mips.Reg(i.left.right.var.name)))
                            r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg('$t3')))
                        else:
                            r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg(i.left.left.var.name), mips.Reg(i.left.right.var.name)))
                    elif type(i.left.left) == tacSpill.Const and type(i.left.right) == tacSpill.Name:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.left.value)))
                        r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg(i.left.right.var.name)))
                    elif type(i.left.right) == tacSpill.Const and type(i.left.left) == tacSpill.Name:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.right.value)))
                        r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg(i.left.left.var.name), mips.Reg('$t2')))
                    elif type(i.left.right) == tacSpill.Const and type(i.left.left) == tacSpill.Const:
                        r.append(mips.LoadI(mips.Reg('$t2'), mips.Imm(i.left.left.value)))
                        r.append(mips.LoadI(mips.Reg('$t3'), mips.Imm(i.left.right.value)))
                        r.append(mips.Op(mips.Mul(), mips.Reg(i.var.name), mips.Reg('$t2'), mips.Reg('$t3')))
                case _:
                    pass
        case tacSpill.Prim():
            match i.left.p:
                case tacSpill.Const():
                    r.append(mips.LoadI(mips.Reg(i.var.name), mips.Imm(i.left.p.value)))
                case tacSpill.Name():
                    if i.var.name == i.left.p.var.name:
                        r.append(mips.Move(mips.Reg('$t2'), mips.Reg(i.left.p.var.name)))
                        r.append(mips.Move(mips.Reg(i.var.name), mips.Reg('$t2')))
                    else:
                        r.append(mips.Move(mips.Reg(i.var.name), mips.Reg(i.left.p.var.name)))
    print(r)
    return r
