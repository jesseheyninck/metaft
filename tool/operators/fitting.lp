% conjunction(B, model(M))
% B: literal_tuple id
% model(M): M is either h(ere) or t(here)
% Conjunction of literals in B holds in World
conjunction(B, model(h)) :- literal_tuple(B),
    hold(L, model(h)) : literal_tuple(B, L), L > 0;
    not hold(L, model(t)) : literal_tuple(B, -L), L > 0.
conjunction(B, model(t)) :- literal_tuple(B),
    hold(L, model(t)) : literal_tuple(B, L), L > 0;
    not hold(L, model(h)) : literal_tuple(B, -L), L > 0.

% hold(A, model(M))
% A: unsigned atom id
% model(M): M is either h(ere) or t(here)
% Atom from rule head must be true if body is satisfied
hold(A, model(t)) :-
    atom_tuple(Head, A), % Assuming rule is normal
    rule(disjunction(Head), normal(Body)),
    conjunction(Body, model(t)).
hold(A, model(h)) :-
    atom_tuple(Head, A), % Assuming rule is normal
    rule(disjunction(Head), normal(Body)),
    conjunction(Body, model(h)).
