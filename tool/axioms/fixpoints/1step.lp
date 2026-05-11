%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Defines fixpoints that require 1 level of iteration to compute
% E.g. kripke kleene and approximator fixpoints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Whether operator has reached fixpoint at a given step
fp(model(M), step(S)) :-
    model(M),
    step(S+1), % Anti-footgun; otherwise final step is always a fixpoint, Note now it's never a fixpoint!
    not strict_atoms_added(model(M), step(S)), step(S),
    not strict_atoms_removed(model(M), step(S)), step(S).
% Make it possible for the final step to be a fixpoint
fp(model(M), step(S)) :- model(M), step(S), fp(model(M), step(S-1)).
% Whether a step introduces new atoms
strict_atoms_added(model(M), step(S)) :-
    step(S), step(S+1),
    hold(V, model(M), step(S+1)), not hold(V, model(M), step(S)).
% Whether a step removes some atoms
strict_atoms_removed(model(M), step(S)) :-
    step(S), step(S+1),
    not hold(V, model(M), step(S+1)), hold(V, model(M), step(S)).
