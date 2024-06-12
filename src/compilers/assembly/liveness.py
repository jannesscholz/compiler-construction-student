from assembly.common import *
from assembly.graph import Graph
import assembly.tac_ast as tac

def instrDef(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers defined by some instrucution.
    """
    match instr:
        case tac.Assign():
            return set([instr.var])
        case tac.Call():
            if instr.name.name == "input_int":
                r: Optional[tac.ident] = instr.var
                if r is not None:
                    return set([r])
        case _:
            return set()
    return set()

def instrUse(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers used by some instrucution.
    """
    r: set[tac.ident] = set()
    match instr:
        case tac.Assign():
            match instr.left:
                case tac.Prim():
                    match instr.left.p:
                        case tac.Name():
                            r.add(instr.left.p.var)
                        case _:
                            pass
                case tac.BinOp():
                    match instr.left.left:
                        case tac.Name():
                            r.add(instr.left.left.var)
                        case _:
                            pass
                    match instr.left.right:
                        case tac.Name():
                            r.add(instr.left.right.var)
                        case _:
                            pass
        case tac.Call():
            for arg in instr.args:
                match arg:
                    case tac.Name():
                        r.add(arg.var)
                    case _:
                        pass
        case tac.GotoIf():
            match instr.test:
                case tac.Name():
                    r.add(instr.test.var)
                case _:
                    pass
        case _:
            pass
    return r

# Each individual instruction has an identifier. This identifier is the tuple
# (index of basic block, index of instruction inside the basic block)
type InstrId = tuple[int, int]

class InterfGraphBuilder:
    def __init__(self):
        # self.before holds, for each instruction I, to set of variables live before I.
        self.before: dict[InstrId, set[tac.ident]] = {}
        # self.after holds, for each instruction I, to set of variables live after I.
        self.after: dict[InstrId, set[tac.ident]] = {}

    def __liveStart(self, bb: BasicBlock, s: set[tac.ident]) -> set[tac.ident]:
        """
        Given a set of variables s and a basic block bb, __liveStart computes
        the set of variables live at the beginning of bb, assuming that s
        are the variables live at the end of the block.

        Essentially, you have to implement the subalgorithm "Computing L_start" from
        slide 46 here. You should update self.after and self.before while traversing
        the instructions of the basic block in reverse.
        """
        for i, instr in enumerate(reversed(bb.instrs)):
            instr_index = len(bb.instrs) - 1 - i
            if i == 0:
                self.after[(bb.index, instr_index)] = s
            else:
                self.after[(bb.index, instr_index)] = self.before[(bb.index, instr_index + 1)]
            self.before[(bb.index, instr_index)] = (self.after[(bb.index, instr_index)] - instrDef(instr)) | instrUse(instr)
        return self.before[(bb.index, 0)]

    def __liveness(self, g: ControlFlowGraph):
        """
        This method computes liveness information and fills the sets self.before and
        self.after.

        You have to implement the algorithm for computing liveness in a CFG from
        slide 46 here.
        """
        for bb in g.values:
            self.before[(bb.index, 0)] = set()
            for i, _ in enumerate(bb.instrs):
                self.before[(bb.index, i)] = set()
                self.after[(bb.index, i)] = set()
        no_change = 0
        while no_change <= len(list(g.values)):
            for bb in reversed(list(g.values)):
                out: set[tac.ident] = set()
                for i in g.succs(bb.index):
                    out |= self.before[(i, 0)]
                old_in_bb: set[tac.ident] = self.before[(bb.index, 0)]
                new_in_bb: set[tac.ident] = self.__liveStart(bb, out)
                if new_in_bb == old_in_bb:
                    no_change += 1

    def __addEdgesForInstr(self, instrId: InstrId, instr: tac.instr, interfG: InterfGraph):
        """
        Given an instruction and its ID, adds the edges resulting from the instruction
        to the interference graph.

        You should implement the algorithm specified on the slide
        "Computing the interference graph" (slide 50) here.
        """
        for x in instrDef(instr):
            for y in self.after[instrId]:
                match instr:
                    case tac.Assign():
                        if type(instr.left) == tac.Prim and type(instr.left.p) == tac.Name:
                            if instr.var == x and instr.left.p.var == y:
                                continue
                    case _:
                        pass
                if x != y:
                    interfG.addEdge(x, y)

    def build(self, g: ControlFlowGraph) -> InterfGraph:
        """
        This method builds the interference graph. It performs three steps:

        - Use __liveness to fill the sets self.before and self.after.
        - Setup the interference graph as an undirected graph containing all variables
          defined or used by any instruction of any basic block. Initially, the
          graph does not have any edges.
        - Use __addEdgesForInstr to fill the edges of the interference graph.
        """
        self.__liveness(g)
        interfgraph: InterfGraph = Graph(kind="undirected")
        for bb in g.values:
            for instr in bb.instrs:
                idents = instrUse(instr) | instrDef(instr)
                for item in idents:
                    if not interfgraph.hasVertex(item):
                        interfgraph.addVertex(item, None)
        for bb in g.values:
            for i, instr in enumerate(bb.instrs):
                self.__addEdgesForInstr((bb.index, i), instr, interfgraph)
        return interfgraph

def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph:
    builder = InterfGraphBuilder()
    return builder.build(g)
