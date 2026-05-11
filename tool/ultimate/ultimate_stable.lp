
% Combining rule bodies with the same head.
% the body/clause Body is relevant for the (head-)atom Atom
relevantFor(Atom,Tuple) :- rule(disjunction(X),normal(Tuple)), atom_tuple(X,Atom).

% For every head-atom A, we build a SAT-solver with relevant body atoms (X) as universe
true(|X|, A, step(S1, S2)), false(|X|,A,step(S1, S2)) :- relevantFor(A,T), literal_tuple(T,X), step(S1, S2).
true(|X|, A, step(S1, S2)) :- step(S1, S2), relevantFor(A,T), literal_tuple(T,X), hold(|X|, model(h), step(S1, S2)).
false(|X|, A, step(S1, S2)) :- step(S1-1), step(S1, S2), relevantFor(A,T), literal_tuple(T,X), not hold(|X|, model(t), step(S1-1)).

%Helper predicate encoding whether an atom is positive or negative
posin(T,A) :- literal_tuple(T,A), A>0.
negin(T,A) :- literal_tuple(T,-A), A>0.

%% unSatNeg true for the body T relative to head-atom X if:
% 1) every atom that occurs positively in T is true,
% 2) every atom that occurs negatively in T is false.
unsatNeg(T, X, step(S1, S2)) :-
  step(S1, S2),
  relevantFor(X,T),
  true(A,X,step(S1, S2)) : posin(T,A);
  relevantFor(X,T), false(A, X, step(S1, S2)) : negin(T,A).

% If the negation of a literal tuple is unsatisfiable, we derivebot, leading to explosion. The saturation technique ensures that this is only possible if there is no other interpretation
bot(A, step(S1, S2)) :- unsatNeg(T, A, step(S1, S2)).
true(|X|, A, step(S1, S2)) :- bot(A, step(S1, S2)), relevantFor(A,T), literal_tuple(T,X).
false(|X|, A, step(S1, S2)) :- bot(A, step(S1, S2)), relevantFor(A,T), literal_tuple(T,X).

%If bot is derivable (i.e. the disjunction of bodies is a tautology), we derive in the lower bound the atom:
hold(L, model(h), step(S1, S2+1)) :- step(S1, S2+1), bot(L, step(S1, S2)).

%%%%% Upper bound: check for satisfiability by checking whether there is a body that is inconsistent. Only occurs if there is a body that:
% a) contains the same atom positively and negatively
isInconsistent(A, T, step(S1, S2)) :- relevantFor(A,T), posin(T,X), negin(T,X), step(S1, S2).
% b) contains an atom positively which is not contained in the upper bound
isInconsistent(A, T, step(S1, S2)) :- relevantFor(A,T), posin(T,X), not hold(X,model(t),step(S1, S2)), step(S1, S2).
% c) contains an atom negatively which is contained in the lower bound
isInconsistent(A,T,step(S1, S2)) :- relevantFor(A,T), negin(T,X), hold(X,model(h),step(S-1)), step(S1, S2).

% If there is a rule-body that is consistent, we derive the head atom in the upper bound.
isConsistent(A,step(S1, S2)) :- step(S1, S2), relevantFor(A,T), not isInconsistent(A,T,step(S1, S2)).
hold(A,model(t),step(S1,S2+1)) :- step(S1, S2+1), atom_tuple(_,A), isConsistent(A,step(S1, S2)).
