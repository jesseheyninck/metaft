from math import factorial
import csv
from clingo import SolveResult
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import random
import uuid
from clingo.control import Control
from clingox.reify import Reifier
from enum import Enum, StrEnum
from pandas import DataFrame
from pathlib import Path
from time import perf_counter_ns, process_time_ns
from pandas import read_csv
from pandas import Int64Dtype
from tqdm import tqdm
from typing import Any
import re

class Encoding(Enum):
    def __lt__(self, other):
        return self.name < other.name
    NEGATION_WITH_SELF_SUPPORT = ['accept(Y):- edge(X,Y), not accept(X).',
                                  'accept(X):- accept(X).']
    NEGATION_WITHOUT_SELF_SUPPORT = ['accept(Y):- edge(X,Y), not accept(X).']
    COLOURING = ['color(r;g).',
                'vertex(X):- edge(X,Y).',
                'vertex(Y):- edge(X,Y).',
                'other(C1,C2):- color(C1), color(C2), C1!=C2.',
                'otherFilled(V,C):- color(C), other(C,C1), filled(V,C1).',
                'neighbour(V,C):- vertex(V), edge(V,V1), filled(V1,C).',
                'filled(V,C):- vertex(V), color(C), not otherFilled(V,C), not neighbour(V,C).',
                'a:- bot, not a.',
                'filled(V):- filled(V,C).',
                'bot :- not filled(V), vertex(V).',
                'support(V,C) :- justify(V,C).',
                'justify(V,C) :- support(V,C).',
                'filled(V,C) :- support(V,C).']
ENCODING_TO_STR = {
        'Encoding.NEGATION_WITH_SELF_SUPPORT': 'Negative edges with\nself support',
        'Encoding.NEGATION_WITHOUT_SELF_SUPPORT': 'Negative edges without\nself support',
        'Encoding.COLOURING': 'Graph colouring'
}

class Semantics(Enum):
    def __lt__(self, other):
        return self.name < other.name
    PARTIAL_FP = 1
    TOTAL_FP = 2
    PARTIAL_STABLE_FP = 3
    TOTAL_STABLE_FP = 4
    KRIPKE_KLEENE = 5
    WELL_FOUNDED = 6
    CLINGO_STABLE = 7

SEMANTICS_TO_STR = {
    'Semantics.PARTIAL_FP': 'Partial fixpoint',
    'Semantics.TOTAL_FP': 'Total fixpoint',
    'Semantics.PARTIAL_STABLE_FP': 'Partial stable fixpoint',
    'Semantics.TOTAL_STABLE_FP': 'Total stable fixpoint',
    'Semantics.KRIPKE_KLEENE': 'Kripke-Kleene',
    'Semantics.WELL_FOUNDED': 'Well-founded',
    'Semantics.CLINGO_STABLE': 'Clingo stable model'
}

class MetaProgram(StrEnum):
    PARTIAL_FP = '../semantics/partial_fp.lp'
    TOTAL_FP = '../semantics/total_fp.lp'
    PARTIAL_STABLE_FP = '../semantics/partial_stable_fp.lp'
    TOTAL_STABLE_FP = '../semantics/total_stable_fp.lp'
    KRIPKE_KLEENE = '../semantics/kripke-kleene.lp'
    WELL_FOUNDED = '../semantics/well-founded.lp'

DEFAULT_EXPERIMENT_CONFIG = Path('./experiment.csv')
DEFAULT_EXPERIMENT_RESULTS = Path('./experimental_results.csv')

DEFAULT_GRAPH_DIR = Path('./graphs')
DEFAULT_REIFICATION_DIR = Path('./reifications')
DEFAULT_CYCLE_DIR = Path('./cycles')

FIGURE_WIDTH = 8.27
FIGURE_HEIGHT = 4.13
FIGURE_DPI = 72

DF_COLUMNS = ['exp_id',
                'config_n_nodes',
                'config_n_cycles',
                'config_fraction_max_cycles',
                'n_cycles',
                'n_even_cycles',
                'n_odd_cycles',
                'fraction_odd_cycles',
                'cycle_counting_time_ns',
                'encoding',
                'n_reification_rules',
                'reification_time_ns',
                'semantics',
                'solve_result',
                'n_models',
                'n_hold_here',
                'n_hold_there',
                'ground_and_solve_time_ns']
DF_TYPES = {
    'exp_id': str,
    'config_n_nodes': int,
    'config_n_cycles': int,
    'config_fraction_max_cycles': float,
    'n_cycles': int,
    'n_even_cycles': int,
    'n_odd_cycles': int,
    'fraction_odd_cycles': float,
    'cycle_counting_time_ns': int,
    'encoding': str,
    'n_reification_rules': int,
    'reification_time_ns': int,
    'semantics': str,
    'solve_result': str,
    'n_models': int,
    'n_hold_here': "Int64",
    'n_hold_there': "Int64",
    'ground_and_solve_time_ns': "Int64"
}


def perform_experiments(file_in : Path = DEFAULT_EXPERIMENT_CONFIG,
                        file_out : Path = DEFAULT_EXPERIMENT_RESULTS):
    # """Iterates over a given csv file with experiment configurations.
    # Performs a complete experiment for each configuration,
    # then writes the experimental results to disk.

    # Args:
    #     file_in (Path, optional): Path to experiment setup csv. Defaults to Path('./experiment.csv').
    #         Expects .csv with columns: n_nodes,n_cycles,extra_edges,max_cycle_len
    #         where extra_edges=0 and max_cycle_len=3.
    #     file_out (Path, optional): Path fpr experimental results csv. Defaults to Path('./experimental_results.csv').
    # """
    res = []
    
    configs = []
    with open(file_in,'r',newline='') as configFile:
        reader = csv.DictReader(configFile)
        configs = [config for config in reader]

    for config in tqdm(configs):
        perform_experiment(config,res)
    
    res_df = DataFrame(res, columns=DF_COLUMNS)
    res_df.to_csv(file_out)
    
    # TODO graph results
    plot_results(res_df)


def perform_experiment(config: dict[str,str],
                       res: list[tuple[Any, ...]],
                       cycle_dir: Path = DEFAULT_CYCLE_DIR,
                       graph_dir: Path = DEFAULT_GRAPH_DIR,
                       base_reification_dir: Path = DEFAULT_REIFICATION_DIR,
                       ):
    # """Performs a single cycle graph experiment.

    # Args:
    #     config (dict[str,str]): the configuration of the experiment.
    #     res_df (DataFrame): the pandas DataFrame to which the experimental results are appended.
    #     graph_dir (Path, optional): Path to directory for generated graph .lp files. Defaults to Path('./graphs').
    #     reification_dir (Path, optional): Path to directory for reifications of generated graph .lp files. Defaults to Path('./reifications').
    #     cycle_dir (Path, optional): Path to directory for cycles found in generated graphs. Defaults to Path('./cycles').

    # Note:
    #     The file written to file_out contains process time metrics.
    #     These measurements rely on the clock exposed by your OS.
    #     For Windows, this clock updates in units of 15625000 ns.
    #     This means that actual process times under this unit length are reported
    #     as 0.
    # """
    assert Path.is_dir(graph_dir)
    assert Path.is_dir(base_reification_dir)
    assert Path.is_dir(cycle_dir)
    assert config['n_nodes'].isdigit()
    assert config['n_cycles'].isdigit()

    exp_id = uuid.uuid4()

    nodes, edges = generate_graph(n_nodes=int(config['n_nodes']),
                                  n_cycles=int(config['n_cycles']),
                                  extra_edges=0,
                                  max_cycle_len=3)

    # Counting (odd/even) cycles and writing cycles to disk
    clock_start = perf_counter_ns()
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    cycles = nx.simple_cycles(graph)
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
    fraction_odd_cycles = n_odd_cycles / n_cycles
    cycle_counting_time_ns = perf_counter_ns() - clock_start

    # Creating lp representation of graph (without encoding)
    graph_program_lines = []
    for u, v in sorted(edges):
        rule = f'edge({u},{v}).'
        graph_program_lines.append(rule)
    graph_program = '\n'.join(graph_program_lines)
    graph_file = graph_dir.joinpath(f'{exp_id}.lp')
    with open(graph_file,'w') as f:
        f.write(graph_program)

    for encoding in Encoding:
        reification_dir = base_reification_dir.joinpath(encoding.name)
        reification_dir.mkdir(parents=True,exist_ok=True)

        # Reifying the graph logic program
        clock_start = perf_counter_ns()
        reification = []
        reifier = Reifier(lambda x: reification.append(str(x)+'.'))
        ctl = Control()
        ctl.configuration.solve.models = 0
        ctl.register_observer(reifier)
        encoded_graph_program = '\n'.join(encoding.value) + '\n' + graph_program
        ctl.add("base",[],encoded_graph_program)
        ctl.ground([("base", [])])
        n_reification_rules = len(reification)
        reification = '\n'.join(reification)
        reification_file = reification_dir.joinpath(f'{exp_id}.rlp')
        with open(reification_file,'w') as f:
            f.write(reification)
        reification_time_ns = perf_counter_ns() - clock_start

        # We define a function to log to the df, fixing all the previous values
        def add_result(semantics: Semantics,
                        solve_result: str,
                        n_models: int,
                        n_hold_here: int,
                        n_hold_there: int,
                        ground_and_solve_time_ns: int) -> None:
            res.append((exp_id,
                            int(config['n_nodes']),
                            int(config['n_cycles']),
                            int(config['n_cycles'])/factorial(int(config['n_nodes'])),
                            n_cycles,
                            n_even_cycles,
                            n_odd_cycles,
                            fraction_odd_cycles,
                            cycle_counting_time_ns,
                            encoding,
                            n_reification_rules,
                            reification_time_ns,
                            semantics,
                            solve_result,
                            n_models,
                            n_hold_here,
                            n_hold_there,
                            ground_and_solve_time_ns))

        # Solving for stable models with Clingo
        clock_start = perf_counter_ns()
        models = []
        solve_result = ctl.solve(on_model=models.append)
        n_models = len(models)
        ground_and_solve_time_ns = perf_counter_ns() - clock_start
        add_result(Semantics.CLINGO_STABLE,
                    solve_result,
                    n_models,
                    pd.NA,
                    pd.NA,
                    ground_and_solve_time_ns)

        # Solving for partial stable models with meta program
        (solve_result,
        n_models,
        n_hold_here,
        n_hold_there,
        ground_and_solve_time_ns
        ) = solve_with_meta_program(MetaProgram.PARTIAL_STABLE_FP, reification)
        add_result(Semantics.PARTIAL_STABLE_FP,
                    solve_result,
                    n_models,
                    n_hold_here,
                    n_hold_there,
                    ground_and_solve_time_ns)

        # Solving for (AFT-style) total stable models with meta program
        (solve_result,
        n_models,
        n_hold_here,
        n_hold_there,
        ground_and_solve_time_ns
        ) = solve_with_meta_program(MetaProgram.TOTAL_STABLE_FP, reification)
        add_result(Semantics.TOTAL_STABLE_FP,
                    solve_result,
                    n_models,
                    n_hold_here,
                    n_hold_there,
                    ground_and_solve_time_ns)
        
        # Solving for partial supported models with meta program
        (solve_result,
        n_models,
        n_hold_here,
        n_hold_there,
        ground_and_solve_time_ns
        ) = solve_with_meta_program(MetaProgram.PARTIAL_FP, reification)
        add_result(Semantics.PARTIAL_FP,
                    solve_result,
                    n_models,
                    n_hold_here,
                    n_hold_there,
                    ground_and_solve_time_ns)

        # Solving for total supported models with meta program
        (solve_result,
        n_models,
        n_hold_here,
        n_hold_there,
        ground_and_solve_time_ns
        ) = solve_with_meta_program(MetaProgram.TOTAL_FP, reification)
        add_result(Semantics.TOTAL_FP,
                    solve_result,
                    n_models,
                    n_hold_here,
                    n_hold_there,
                    ground_and_solve_time_ns)
        
        # Solving for Kripke-Kleene model with meta program
        (solve_result,
        n_models,
        n_hold_here,
        n_hold_there,
        ground_and_solve_time_ns
        ) = solve_with_lfp_meta_program(MetaProgram.KRIPKE_KLEENE, reification)
        add_result(Semantics.KRIPKE_KLEENE,
                    solve_result,
                    n_models,
                    n_hold_here,
                    n_hold_there,
                    ground_and_solve_time_ns)
        
        # Solving for well-founded model with meta program
        (solve_result,
        n_models,
        n_hold_here,
        n_hold_there,
        ground_and_solve_time_ns
        ) = solve_with_lfp_meta_program(MetaProgram.WELL_FOUNDED, reification)
        add_result(Semantics.WELL_FOUNDED,
                    solve_result,
                    n_models,
                    n_hold_here,
                    n_hold_there,
                    ground_and_solve_time_ns)


def solve_with_meta_program(meta_program: MetaProgram,
                            reified_logic_program: str) -> tuple[SolveResult,int,int,int,int]:
    clock_start = perf_counter_ns()
    models = []
    ctl = Control()
    ctl.configuration.solve.models = 0
    ctl.load(meta_program.value)
    ctl.add("base",[],reified_logic_program)
    ctl.ground([("base", [])])
    solve_result = ctl.solve(on_model = models.append)
    n_models = len(models)
    elapsed_time_ns = perf_counter_ns() - clock_start
    return (solve_result, n_models, pd.NA, pd.NA, elapsed_time_ns)

def solve_with_lfp_meta_program(meta_program: MetaProgram,
                                reified_logic_program: str) -> tuple[SolveResult,int,int,int,int]:
    assert meta_program == MetaProgram.KRIPKE_KLEENE or meta_program == MetaProgram.WELL_FOUNDED
    clock_start = perf_counter_ns()
    ctl = Control()
    ctl.load(meta_program.value)
    ctl.add("base",[],reified_logic_program)
    ctl.ground([("base", [])])
    n_hold_here = 0
    n_hold_there = 0
    def retrieve_holds(model):
        nonlocal n_hold_here
        nonlocal n_hold_there
        h = re.search(r"(?<!\S)here\((?P<x>\d+)\)(?!\S)", str(model))
        if h: n_hold_here = int(h['x'])
        t = re.search(r"(?<!\S)there\((?P<x>\d+)\)(?!\S)", str(model))
        if t: n_hold_there = int(t["x"])
    solve_result = ctl.solve(on_model = retrieve_holds)
    n_models = int(solve_result.satisfiable)
    elapsed_time_ns = perf_counter_ns() - clock_start
    return (solve_result, n_models, n_hold_here, n_hold_there, elapsed_time_ns)


def triple_plot(df: DataFrame,
                    values: str,
                    index: str,
                    x_label: str,
                    y_label: str,
                    title: str | None = None,
                    share_y: bool = False,
                    log_y: bool = False) -> None:
    assert list(df.columns) == DF_COLUMNS

    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(list(Encoding)),
        sharex=False,
        sharey=share_y,
        figsize=[FIGURE_WIDTH,FIGURE_HEIGHT],
        layout='constrained',
        dpi=FIGURE_DPI
    )
    if title: fig.suptitle(title)
    pivot = df.pivot_table(values=values,
                            index=['encoding',index],
                            columns=['semantics'],
                            aggfunc='mean')
    groups = pivot.groupby(level=0)
    for ax, (encoding, sub_df) in zip(axes, groups):
        sub_df = sub_df.droplevel(0)
        sub_df.plot(ax=ax,legend=False,logy=log_y)
        if isinstance(encoding,Encoding): encoding = str(encoding)
        ax.set_title(ENCODING_TO_STR[encoding])
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_box_aspect(1)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles,
               [SEMANTICS_TO_STR[l] for l in labels],
               loc='outside lower center',
               ncols=3,
               mode='expand',
               borderaxespad=0.)    

def plot_results(df : DataFrame):
    assert list(df.columns) == DF_COLUMNS

    # time/n_reif
    triple_plot(df=df,
            values='ground_and_solve_time_ns',
            index='n_reification_rules',
            x_label='n. of rules in reified program',
            y_label='mean time to ground and solve (ns)',
            # title='Time to ground and solve by size of reified program',
            share_y=True,
            log_y=True)

    # # time/n_models
    # plot(df=df,
    #         values='ground_and_solve_time_ns',
    #         index='n_models',
    #         x_label='n. of models',
    #         y_label='mean time to ground and solve (ns)')

    # # n_reif/gen_n_nodes
    # triple_plot(df=df,
    #         values='n_reification_rules',
    #         index='config_n_nodes',
    #         x_label='n. of nodes in generated graph',
    #         y_label='n. of rules in reified program')
    
    # # n_reif/gen_n_cycles
    # triple_plot(df=df,
    #         values='n_reification_rules',
    #         index='config_n_cycles',
    #         x_label='n. of cycles inserted into graph',
    #         y_label='n. of rules in reified program')
    
    # # n_reif/(gen_n_cycles/gen_n_nodes!)
    # plot(df=df,
    #         values='n_reification_rules',
    #         index='config_fraction_max_cycles',
    #         x_label='fraction of possible cycles inserted into graph',
    #         y_label='n. of rules in reified program')
    
    # # n_reif/n_cycles
    # triple_plot(df=df,
    #         values='n_reification_rules',
    #         index='n_cycles',
    #         x_label='n. of cycles in graph',
    #         y_label='n. of rules in reified program')

    # n_models per experiment, triple
    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(list(Encoding)),
        sharex=False,
        sharey=True,
        figsize=[FIGURE_WIDTH,FIGURE_HEIGHT],
        layout='constrained',
        dpi=FIGURE_DPI
    )
    # fig.suptitle('Number of models per Semantics')
    mask = df['semantics'].isin([Semantics.TOTAL_FP,
                                 Semantics.PARTIAL_FP,
                                 Semantics.TOTAL_STABLE_FP,
                                 Semantics.PARTIAL_STABLE_FP])
    pivot = df[mask].pivot_table(values='n_models',
                                    index=['encoding','exp_id'],
                                    columns=['semantics'],
                                    aggfunc='mean')
    groups = pivot.groupby(level=0)
    for ax, (encoding, sub_df) in zip(axes, groups):
        sub_df = sub_df.droplevel(0)
        sub_df.plot(ax=ax,legend=False,logy=False)
        if isinstance(encoding,Encoding): encoding = str(encoding)
        ax.set_title(ENCODING_TO_STR[encoding])
        ax.set_xlabel('experiment instance')
        ax.set_ylabel('n. of models')
        ax.set_xticklabels([])
        ax.set_box_aspect(1)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles,
               [SEMANTICS_TO_STR[l] for l in labels],
               loc='outside lower center',
               ncols=2,
               mode='expand',
               borderaxespad=0.)

    # n_models per experiment, single
    fig, ax = plt.subplots(
        nrows=1,
        ncols=1,
        squeeze=True,
        figsize=[FIGURE_WIDTH,FIGURE_HEIGHT],
        layout='constrained',
        dpi=FIGURE_DPI)
    mask = df['semantics'].isin([Semantics.TOTAL_FP,
                                 Semantics.PARTIAL_FP,
                                 Semantics.TOTAL_STABLE_FP,
                                 Semantics.PARTIAL_STABLE_FP])
    pivot = df[mask].pivot_table(values='n_models',
                                    index=['encoding','exp_id'],
                                    columns=['semantics'],
                                    aggfunc='mean')
    pivot.plot(ax=ax,legend=False,)
    # ax.set_title('Number of models per Semantics')
    ax.set_xlabel('experiment instance')
    ax.set_ylabel('n. of models')
    ax.set_xticklabels([])
    ax.set_box_aspect(0.33)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles,
               [SEMANTICS_TO_STR[l] for l in labels],
               loc='outside lower center',
               ncols=2,
               mode='expand',
               borderaxespad=0.)

    # # n_models/n_odd
    # triple_plot(df=df,
    #         values='n_models',
    #         index='n_odd_cycles',
    #         x_label='n. of odd cycles in graph',
    #         y_label='n. of models')
    
    # # n_models/frac_odd
    # triple_plot(df=df,
    #         values='n_models',
    #         index='fraction_odd_cycles',
    #         x_label='fraction of cycles in graph odd',
    #         y_label='n. of models')
    
    # # n_models/n_reification_rules
    # triple_plot(df=df,
    #         values='n_models',
    #         index='n_reification_rules',
    #         x_label='n. of rules in reified program',
    #         y_label='n. of models')
    
    # # n_models/n_cycles
    # triple_plot(df=df,
    #         values='n_models',
    #         index='n_cycles',
    #         x_label='n. of cycles in graph',
    #         y_label='n. of models')
    
    # KK vs WF size, triple
    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(list(Encoding)),
        sharex=False,
        sharey=True,
        figsize=[FIGURE_WIDTH,FIGURE_HEIGHT],
        layout='constrained',
        dpi=FIGURE_DPI
    )
    # fig.suptitle('Precision of Kripke-Kleene and well-founded')
    mask = df['semantics'].isin([Semantics.KRIPKE_KLEENE,Semantics.WELL_FOUNDED])
    pivot = df[mask].pivot_table(values=['n_hold_there','n_hold_here'],
                                    index=['encoding','exp_id'],
                                    columns=['semantics'],
                                    aggfunc='mean')
    groups = pivot.groupby(level=0)
    for ax, (encoding, sub_df) in zip(axes, groups):
        sub_df = sub_df.droplevel(0)
        sub_df.plot(ax=ax,legend=False,logy=False)
        if isinstance(encoding,Encoding): encoding = str(encoding)
        ax.set_title(ENCODING_TO_STR[encoding])
        ax.set_xlabel('experiment instance')
        ax.set_ylabel('n. of atoms true here/there')
        ax.set_xticklabels([])
        ax.set_box_aspect(1)
    handles, labels = axes[0].get_legend_handles_labels()
    def transform_label(label):
        [model, semantics] = str(label)[1:-1].split(', ')
        model = 'here' if model == 'n_hold_here' else 'there'
        semantics = SEMANTICS_TO_STR[semantics]
        return ', '.join([semantics,model])
    fig.legend(handles,
               [transform_label(l) for l in labels],
               loc='outside lower center',
               ncols=2,
               mode='expand',
               borderaxespad=0.)

    # KK vs WF size, single
    fig, ax = plt.subplots(
        nrows=1,
        ncols=1,
        squeeze=True,
        figsize=[FIGURE_WIDTH,FIGURE_HEIGHT],
        layout='constrained',
        dpi=FIGURE_DPI)
    mask = df['semantics'].isin([Semantics.KRIPKE_KLEENE,Semantics.WELL_FOUNDED])
    pivot = df[mask].pivot_table(values=['n_hold_there','n_hold_here'],
                                    index=['encoding','exp_id'],
                                    columns=['semantics'],
                                    aggfunc='mean')
    pivot.plot(ax=ax,legend=False,)
    # ax.set_title('Precision of Kripke-Kleene and well-founded')
    ax.set_xlabel('experiment instance')
    ax.set_ylabel('n. of atoms true here/there')
    ax.set_xticklabels([])
    ax.set_box_aspect(0.33)
    handles, labels = ax.get_legend_handles_labels()
    def transform_label(label):
        [model, semantics] = str(label)[1:-1].split(', ')
        model = 'here' if model == 'n_hold_here' else 'there'
        semantics = SEMANTICS_TO_STR[semantics]
        return ', '.join([semantics,model])
    fig.legend(handles,
               [transform_label(l) for l in labels],
               loc='outside lower center',
               ncols=2,
               mode='expand',
               borderaxespad=0.)

    plt.show()


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
    def parse_encoding(value: str) -> Encoding:
        name = value.split(".")[-1]
        return Encoding[name]
    def parse_semantics(value: str) -> Semantics:
        name = value.split(".")[-1]
        return Semantics[name]

    df = pd.read_csv(DEFAULT_EXPERIMENT_RESULTS,header=0,index_col=0,dtype=DF_TYPES)
    df["encoding"] = df["encoding"].apply(parse_encoding)
    df['semantics'] = df['semantics'].apply(parse_semantics)
    plot_results(df=df)

    # perform_experiments()