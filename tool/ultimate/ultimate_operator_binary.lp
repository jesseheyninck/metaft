
% Combining rule bodies with the same head.
% the body/clause Body is relevant for the (head-)atom Atom
relevantFor(Atom, Body) :- rule(disjunction(X), normal(Body)), atom_tuple(X, Atom).

% For every head-atom A, we build a SAT-solver with relevant body atoms (X) as universe
true(|X|,A), false(|X|,A) :- relevantFor(A,T), literal_tuple(T,X).
true(|X|, A) :-
    relevantFor(A, T),
    literal_tuple(T, X),
    hold(|X|, model(h), step(0)).
false(|X|, A) :-
    relevantFor(A, T),
    literal_tuple(T, X),
    not hold(|X|, model(t), step(0)).

% Helper predicate encoding whether an atom is positive or negative
posin(T, A) :- literal_tuple(T, A), A>0.
negin(T, A) :- literal_tuple(T, -A), A>0.

unsatNeg(T, X) :-
    relevantFor(X, T),
    true(A, X) : posin(T, A);
    false(A, X) : negin(T, A).

% unsatNeg true for the body T relative to head-atom X if:
% 1) every atom that occurs positively in T is true,
% 2) every atom that occurs negatively in T is false.
% In other words, the body has to be true, which means it's negation is unsatisfiabile.
% Thus, what happens is that, due to the way saturation works, clingo will look for an assignment of true(X, A) and false(X, A) that does not satisfy the body of T, and only if this doesn't exist, will bot be derived
% In other words, bot is derived only if at least one body of a rule for p (i.e. a disjunct) is true in every possible interpretation.

% If the negation of a literal tuple is unsatisfiable, we derive bot, leading to explosion. The saturation technique ensures that this is only possible if there is no other interpretation
bot(A) :- unsatNeg(T, A).
true(|X|, A) :- bot(A), relevantFor(A, T), literal_tuple(T, X).
false(|X|, A) :- bot(A), relevantFor(A, T), literal_tuple(T, X).

% If bot is derivable (i.e. the disjunction of bodies is a tautology), we derive in the lower bound the atom:
hold(L, model(h), step(I+1)) :- step(I),  bot(L).


%%%%% Upper bound: check for satisfiability by checking whether there is a body that is inconsistent. Only occurs if there is a body that:
% a) contains the same atom positively and negatively
isInconsistent(A, T) :- relevantFor(A, T), posin(T, X), negin(T, X).
% b) contains an atom positively which is not contained in the upper bound
isInconsistent(A, T) :- relevantFor(A, T), posin(T, X), not hold(X, model(t), step(I)), step(I).
% c) contains an atom negatively which is contained in the lower bound
isInconsistent(A, T) :- relevantFor(A, T) , negin(T, X), hold(X, model(h), step(I)), step(I).

% If there is a rule that is inconsistent
isConsistent(A) :- relevantFor(A, T), not isInconsistent(A, T).
hold(A, model(t), step(I+1)) :- step(I), atom_tuple(_, A), isConsistent(A).
