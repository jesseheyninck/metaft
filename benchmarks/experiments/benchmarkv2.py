import uuid
import csv
from pathlib import Path
import pandas as pd
from clingo.control import Control
from clingox.reify import Reifier
import random
import networkx as nx
from time import perf_counter_ns, process_time_ns
from tqdm import tqdm

partial_fp = '../semantics/partial_fp.lp'
total_fp = '../semantics/total_fp.lp'
partial_stable_fp = '../semantics/partial_stable_fp.lp'
total_stable_fp = '../semantics/total_stable_fp.lp'
kripkekleene = '../semantics/kripke-kleene.lp'
wellfounded = '../semantics/well-founded.lp'

def experiment(file_in : Path = Path('./experiment.csv'),
               file_out : Path = Path('./experimental_results.csv'),
               graph_dir : Path = Path('./graphs'), 
               reification_dir : Path = Path('./reifications'),
               cycle_dir : Path = Path('./cycles')):
    """Performs a cycle graph experiment.

    Args:
        file_in (Path, optional): Path to experiment setup csv. Defaults to Path('./experiment.csv').
            Expects .csv with columns: n_nodes,n_cycles,extra_edges,max_cycle_len
            where extra_edges=0 and max_cycle_len=3.
        file_out (Path, optional): Path fpr experimental results csv. Defaults to Path('./experimental_results.csv').
        graph_dir (Path, optional): Path to directory for generated graph .lp files. Defaults to Path('./graphs').
        reification_dir (Path, optional): Path to directory for reifications of generated graph .lp files. Defaults to Path('./reifications').
        cycle_dir (Path, optional): Path to directory for cycles found in generated graphs. Defaults to Path('./cycles').

    Note:
        The file written to file_out contains process time metrics.
        These measurements rely on the clock exposed by your OS.
        For Windows, this clock updates in units of 15625000 ns.
        This means that actual process times under this unit length are reported
        as 0.
    """
    assert Path.is_dir(graph_dir)
    assert Path.is_dir(reification_dir)
    assert Path.is_dir(cycle_dir)

    res = pd.DataFrame(columns=['exp_id',
                                'gen_n_nodes',
                                'gen_n_cycles',
                                'gen_extra_edges',
                                'gen_max_cycle_len',
                                'total_wall_time_ns',
                                'total_process_time_ns',
                                'n_cycles',
                                'n_even_cycles',
                                'n_odd_cycles',
                                'cycle_wall_time_ns',
                                'cycle_process_time_ns',
                                'reification_wall_time_ns',
                                'reification_process_time_ns',
                                'n_clingo_stable_models',
                                'clingo_stable_solve_result',
                                'clingo_stable_wall_time_ns',
                                'clingo_stable_process_time_ns',
                                'n_partial_stable_models',
                                'partial_stable_solve_result',
                                'partial_stable_wall_time_ns',
                                'partial_stable_process_time_ns',
                                'n_total_stable_models',
                                'total_stable_solve_result',
                                'total_stable_wall_time_ns',
                                'total_stable_process_time_ns',
                                'n_partial_supported_models',
                                'partial_supported_solve_result',
                                'partial_supported_wall_time_ns',
                                'partial_supported_process_time_ns',
                                'n_total_supported_models',
                                'total_supported_solve_result',
                                'total_supported_wall_time_ns',
                                'total_supported_process_time_ns',
                                'n_kripkekleene',
                                'kripkekleene_result',
                                'kripkekleene_wall_time_ns',
                                'kripkekleene_process_time_ns',
                                'n_wellfounded',
                                'wellfounded_result',
                                'wellfounded_wall_time_ns',
                                'wellfounded_process_time_ns'])

    experiments = []
    with open(file_in,'r',newline='') as graphSettings:
        reader = csv.DictReader(graphSettings)
        experiments = [exp for exp in reader]
    for exp in tqdm(experiments):
        wall_clock_start = perf_counter_ns()
        process_clock_start = process_time_ns()

        exp_id = uuid.uuid4()

        nodes, edges = generate_graph(int(exp['n_nodes']),
                                      int(exp['n_cycles']),
                                      int(exp['extra_edges']),
                                      int(exp['max_cycle_len']))

        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        cycles = nx.simple_cycles(G)
        n_even_cycles = 0
        n_odd_cycles = 0
        n_cycles = 0
        cycles_file = cycle_dir.joinpath(f'{exp_id}.txt')
        with open(cycles_file, 'w') as f:
            for c in cycles:
                n_cycles += 1
                if len(c) % 2 == 0:
                    n_even_cycles += 1
                else:
                    n_odd_cycles += 1
                f.write(str(c)+'\n')
        cycle_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        cycle_process_time_ns = process_time_ns() - temp_process_clock_start

        graph_program_lines = []
        graph_file = graph_dir.joinpath(f'{exp_id}.lp')
        with open(graph_file,'w') as f:
            encoding = 'color(r;g). vertex(X):- edge(X,Y). vertex(Y):- edge(X,Y). other(C1,C2):- color(C1), color(C2), C1!=C2. otherFilled(V,C):- color(C), other(C,C1), filled(V,C1). neighbour(V,C):- vertex(V), edge(V,V1), filled(V1,C). filled(V,C):- vertex(V), color(C), not otherFilled(V,C), not neighbour(V,C). a:- bot, not a. filled(V):- filled(V,C). bot :- not filled(V), vertex(V). support(V,C) :- justify(V,C). justify(V,C) :- support(V,C). filled(V,C) :- support(V,C).'
            f.write(encoding + '\n')
            graph_program_lines.append(encoding)
            for u, v in sorted(edges):
                rule = f'edge({u},{v}).'
                f.write(rule + '\n')
                graph_program_lines.append(rule)
        graph_program = '\n'.join(graph_program_lines)

        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        reification = []
        reifier = Reifier(lambda x: reification.append(str(x)+'.'))
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.register_observer(reifier)
        ctl.add("base",[],graph_program)
        ctl.ground([("base", [])])
        reification = '\n'.join(reification)
        reification_file = reification_dir.joinpath(f'{exp_id}.rlp')
        with open(reification_file,'w') as f:
            f.write(reification)
        reification_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        reification_process_time_ns = process_time_ns() - temp_process_clock_start

        #stable (clingo)
        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        clingo_stable_models = []
        clingo_stable_solve_result = ctl.solve(on_model = clingo_stable_models.append)
        n_clingo_stable_models = len(clingo_stable_models)
        clingo_stable_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        clingo_stable_process_time_ns = process_time_ns() - temp_process_clock_start

        # partial stable
        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        partial_stable_models = []
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.load(partial_stable_fp)
        ctl.add("base",[],reification)
        ctl.ground([("base", [])])
        partial_stable_solve_result = ctl.solve(on_model = partial_stable_models.append)
        n_partial_stable_models = len(partial_stable_models)
        partial_stable_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        partial_stable_process_time_ns = process_time_ns() - temp_process_clock_start

        # total stable (AFT-style)
        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        total_stable_models = []
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.load(total_stable_fp)
        ctl.add("base",[],reification)
        ctl.ground([("base", [])])
        total_stable_solve_result = ctl.solve(on_model = total_stable_models.append)
        n_total_stable_models = len(total_stable_models)
        total_stable_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        total_stable_process_time_ns = process_time_ns() - temp_process_clock_start

        # partial supported models 

        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        partial_supported_models = []
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.load(partial_fp)
        ctl.add(reification)
        ctl.ground([("base", [])])
        partial_supported_solve_result = ctl.solve(on_model = partial_supported_models.append)
        n_partial_supported_models = len(partial_supported_models)
        partial_supported_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        partial_supported_process_time_ns = process_time_ns() - temp_process_clock_start

         # total supported models 


        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        total_supported_models = []
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.load(partial_fp)
        ctl.add(reification)
        ctl.ground([("base", [])])
        total_supported_solve_result = ctl.solve(on_model = total_supported_models.append)
        n_total_supported_models = len(total_supported_models)
        total_supported_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        total_supported_process_time_ns = process_time_ns() - temp_process_clock_start

         # kripke-kleene model

        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        kripkekleenemodels = []
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.load(kripkekleene)
        ctl.add(reification)
        ctl.ground([("base", [])])
        kripkekleene_result = ctl.solve(on_model = kripkekleenemodels.append)
        n_kripkekleene = len(kripkekleenemodels)
        kripkekleene_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        kripkekleene_process_time_ns = process_time_ns() - temp_process_clock_start

        # well-founded model

        temp_wall_clock_start = perf_counter_ns()
        temp_process_clock_start = process_time_ns()
        wellfoundedmodels = []
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.load(wellfounded)
        ctl.add(reification)
        ctl.ground([("base", [])])
        wellfounded_result = ctl.solve(on_model = wellfoundedmodels.append)
        n_wellfounded = len(wellfoundedmodels)
        wellfounded_wall_time_ns = perf_counter_ns() - temp_wall_clock_start
        wellfounded_process_time_ns = process_time_ns() - temp_process_clock_start

        total_wall_time_ns = perf_counter_ns() - wall_clock_start
        total_process_time_ns = process_time_ns() - process_clock_start
        
        res.loc[len(res)] = [exp_id,
                             exp['n_nodes'],
                             exp['n_cycles'],
                             exp['extra_edges'],
                             exp['max_cycle_len'],
                             total_wall_time_ns,
                             total_process_time_ns,
                             n_cycles,
                             n_even_cycles,
                             n_odd_cycles,
                             cycle_wall_time_ns,
                             cycle_process_time_ns,
                             reification_wall_time_ns,
                             reification_process_time_ns,
                             n_clingo_stable_models,
                             clingo_stable_solve_result,
                             clingo_stable_wall_time_ns,
                             clingo_stable_process_time_ns,
                             n_partial_stable_models,
                             partial_stable_solve_result,
                             partial_stable_wall_time_ns,
                             partial_stable_process_time_ns,
                            n_total_stable_models,
                            total_stable_solve_result,
                            total_stable_wall_time_ns,
                            total_stable_process_time_ns,
                            n_partial_supported_models,
                            partial_supported_solve_result,
                            partial_supported_wall_time_ns,
                            partial_supported_process_time_ns,
                            n_total_supported_models,
                            total_supported_solve_result,
                            total_supported_wall_time_ns,
                            total_supported_process_time_ns,
                            n_kripkekleene,
                            kripkekleene_result,
                            kripkekleene_wall_time_ns,
                            kripkekleene_process_time_ns,
                            n_wellfounded,
                            wellfounded_result,
                            wellfounded_wall_time_ns,
                            wellfounded_process_time_ns]
    res.to_csv(file_out)

def generate_graph(n_nodes=20, n_cycles=10, extra_edges=30, max_cycle_len=6):
    assert max_cycle_len >= 2, "max_cycle_len should be at least 2"
    assert max_cycle_len <= n_nodes, "max_cycle_len can be at most n_nodes"

    nodes = list(range(n_nodes))
    edges = set()

    # --- Step 1: Insert cycles explicitly ---
    for _ in range(n_cycles):
        cycle_len = random.randint(2, max_cycle_len)
        cycle_nodes = random.sample(nodes, cycle_len)

        for i in range(cycle_len):
            u = cycle_nodes[i]
            v = cycle_nodes[(i + 1) % cycle_len]
            edges.add((u, v))

    # --- Step 2: Add extra random edges ---
    for _ in range(extra_edges):
        u, v = random.sample(nodes, 2)
        edges.add((u, v))
        # TODO adding random edges may shortcut explicitly added cycles

    return nodes, edges

if __name__ == "__main__":
    experiment()
