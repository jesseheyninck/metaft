# Installation
0. Change current directory to the folder containing this readme. E.g. `cd modularized`
(Steps 1 and 2 optional if you instead want to install python packages globally)
1. Create python virtual env
```
python -m venv env
```
2. (Any time project is opened) Activate virtual env
```
source env/bin/activate
```
3. Install Python dependencies
```
pip install -r requirements.txt
```

# Usage
For semantics based on a user-defined operator (or the Fitting operator) program can be ran by using 
```
python tool.py SEMANTICS OPERATOR PROGRAM
```
Where `SEMANTICS` can be one of the following:
`fixpoints`, `kripke-kleene`, `stable-fixpoints`,
`OPERATOR` indicates the file of the operator (e.g. `operators\fitting.lp` for the Fitting-Operator), and `PROGRAM` indicates the file of the normal logic program (e.g. `tests\long_chain.lp`).

Alternatively, one can generate the meta-program for a semantics using 
```
python tool.py SEMANTICS OPERATOR
```
For semantics based on the ultimate operator, one can run:
```
python tool.py SEMANTICS PROGRAM
```
where `SEMANTICS` can be one of the following:
`ultimate-fixpoints`, `ultimate-kripke-kleene`, `ultimate-stable-fixpoints`, or `ultimate-well-founded`
