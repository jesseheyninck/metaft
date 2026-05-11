%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Defines fixpoints that require 2 level of iteration to compute
% 1step.lp should also be imported
% E.g. stable fixpoints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Whether operator has reached fixpoint at a given step
fp(model(M), step(S1, S2)) :-
    model(M),
    step(S1, S2+1), % Anti-footgun; otherwise final step is always a fixpoint,
    not strict_atoms_added(model(M), step(S1, S2)), step(S1, S2),
    not strict_atoms_removed(model(M), step(S1, S2)), step(S1, S2).
% Make it possible for the final step to be a fixpoint
fp(model(M), step(S1, S2)) :- model(M), step(S1, S2), fp(model(M), step(S1, S2-1)).
% Whether a step introduces new atoms
strict_atoms_added(model(M), step(S1, S2)) :-
    step(S1, S2), step(S1, S2+1),
    hold(V, model(M), step(S1, S2+1)), not hold(V, model(M), step(S1, S2)).
% Whether a step removes some atoms
strict_atoms_removed(model(M), step(S1, S2)) :-
    step(S1, S2), step(S1, S2+1),
    not hold(V, model(M), step(S1, S2+1)), hold(V, model(M), step(S1, S2)).
