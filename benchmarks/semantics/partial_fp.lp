

%!! Program generated using the base 'operators/fitting.lp'
conjunction(B,model(h),step(S)) :- step(S); literal_tuple(B); hold(L,model(h),step(S)): literal_tuple(B,L), L > 0; not hold(L,model(t),step(S)): literal_tuple(B,-L), L > 0.
conjunction(B,model(t),step(S)) :- step(S); literal_tuple(B); hold(L,model(t),step(S)): literal_tuple(B,L), L > 0; not hold(L,model(h),step(S)): literal_tuple(B,-L), L > 0.
hold(A,model(t),step((S+1))) :- step((S+1)); atom_tuple(Head,A); rule(disjunction(Head),normal(Body)); conjunction(Body,model(t),step(S)).
hold(A,model(h),step((S+1))) :- step((S+1)); atom_tuple(Head,A); rule(disjunction(Head),normal(Body)); conjunction(Body,model(h),step(S)).

%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/fixpoints/1step.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Defines fixpoints that require 1 level of iteration to compute
% E.g. kripke kleene and approximator fixpoints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Whether operator has reached fixpoint at a given step
fp(model(M), step(S)) :-
    model(M),
    step(S+1), % Anti-footgun; otherwise final step is always a fixpoint, Note now it's never a fixpoint!
    not strict_partial_postfp(model(M), step(S)), step(S),
    not strict_partial_prefp(model(M), step(S)), step(S).
% Make it possible for the final step to be a fixpoint
fp(model(M), step(S)) :- model(M), step(S), fp(model(M), step(S-1)).
% Whether a step introduces new atoms
strict_partial_postfp(model(M), step(S)) :-
    step(S), step(S+1),
    hold(V, model(M), step(S+1)), not hold(V, model(M), step(S)).
% Whether a step removes some atoms
strict_partial_prefp(model(M), step(S)) :-
    step(S), step(S+1),
    not hold(V, model(M), step(S+1)), hold(V, model(M), step(S)).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/fixpoints/iterate_generic_1step.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Removes inconsistent assignments and constrains to look for
% fixpoints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% What's true here, is true there as well. 
hold(L, model(t), step(I)) :- hold(L, model(h), step(I)).

% Discard answer sets that aren't fixpoints
fp(model(M)) :- fp(model(M), step(_)).
:- not fp(model(M)), model(M).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/output_1step.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Atoms required to convert solver atom ids to their textual form
% Should be included everywhere
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

holdsIn(Atom, model(M), step(S)) :-
    model(M), output(Atom, B), literal_tuple(B, A), hold(A, model(M), step(S)).
% Handle empty tuples (tautology)
occupied_literal_tuple(B) :- literal_tuple(B, _).
holdsIn(Atom, model(M), step(S)) :-
    step(S),  model(M), output(Atom, B), not occupied_literal_tuple(B).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/models.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Should be included everywhere
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

model(h;t).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/fixpoints/iterate_everything.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Provides a choice rule to say that any atom appearing a in a
% head of a rule can be any truth value
% iterate_generic_1step.lp is required to remove inconsistent
% assignments
%
% An alternative to iterate_lfp.lp
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

step(-1;0).
% Choose atoms in heads to be in here or there.
{ hold(A, model(M), step(-1)) } :- model(M), rule(disjunction(H),_), atom_tuple(H,A).

