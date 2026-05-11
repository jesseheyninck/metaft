%!! Program generated using the base 'operators/fitting.lp'
conjunction(B,model(h),step(S1,S2)) :- step(S1,S2); literal_tuple(B); hold(L,model(h),step(S1,S2)): literal_tuple(B,L), L > 0; not hold(L,model(t),step((S1-1))): literal_tuple(B,-L), L > 0.
conjunction(B,model(t),step(S1,S2)) :- step(S1,S2); literal_tuple(B); hold(L,model(t),step(S1,S2)): literal_tuple(B,L), L > 0; not hold(L,model(h),step((S1-1))): literal_tuple(B,-L), L > 0.
hold(A,model(t),step(S1,(S2+1))) :- step(S1,(S2+1)); atom_tuple(Head,A); rule(disjunction(Head),normal(Body)); conjunction(Body,model(t),step(S1,S2)).
hold(A,model(h),step(S1,(S2+1))) :- step(S1,(S2+1)); atom_tuple(Head,A); rule(disjunction(Head),normal(Body)); conjunction(Body,model(h),step(S1,S2)).

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

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/fixpoints/iterate_generic_2step.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% To be included with iterate_generic_1step.lp for tasks that 
% require multiple levels of iteration (e.g. stable fixpoints)
% this allows computation from nested iteration 
% e.g. step(0, 1), step(0, 2), step(0, 3)
% to carry forward to the step step(1)
% which subsequently carries to the substeps
% step(1, 0), step(1, 1), etc
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


% If something holds for a substep, then it holds for single step
hold(V, model(M), step(S)) :- hold(V, model(M), step(S, _)).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/fixpoints/iterate_lfp.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Gives all atoms a value of undefined
%
% An alternative to iterate_everything.lp
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Initiallly, all head atoms are in there, and here is empty
step(-1).
hold(A, model(t), step(-1)) :- atom_tuple(_, A).
hold(L, model(t), step(-1)) :- literal_tuple(_, L), L >= 0.
hold(L, model(t), step(-1)) :- literal_tuple(_, -L), L >= 0.

% Alternatively: 
% Make all head atoms true
% hold(A, model(t), step(0)) :- rule(disjunction(H),_), atom_tuple(H,A).

    
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

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/fixpoints/2step.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Defines fixpoints that require 2 level of iteration to compute
% 1step.lp should also be imported
% E.g. stable fixpoints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Whether operator has reached fixpoint at a given step
fp(model(M), step(S1, S2)) :-
    model(M),
    step(S1, S2+1), % Anti-footgun; otherwise final step is always a fixpoint,
    not strict_partial_postfp(model(M), step(S1, S2)), step(S1, S2),
    not strict_partial_prefp(model(M), step(S1, S2)), step(S1, S2).
% Make it possible for the final step to be a fixpoint
fp(model(M), step(S1, S2)) :- model(M), step(S1, S2), fp(model(M), step(S1, S2-1)).
% Whether a step introduces new atoms
strict_partial_postfp(model(M), step(S1, S2)) :-
    step(S1, S2), step(S1, S2+1),
    hold(V, model(M), step(S1, S2+1)), not hold(V, model(M), step(S1, S2)).
% Whether a step removes some atoms
strict_partial_prefp(model(M), step(S1, S2)) :-
    step(S1, S2), step(S1, S2+1),
    not hold(V, model(M), step(S1, S2+1)), hold(V, model(M), step(S1, S2)).

    
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

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/output_2step.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Atoms required to convert solver atom ids to their textual form
% To be included with output_1step.lp whenever nested steps are
% used
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

holdsIn(Atom, model(M), step(S1, S2)) :-
    model(M), output(Atom, B), literal_tuple(B, A), hold(A, model(M), step(S1, S2)).
% Handle empty tuples (tautology)
occupied_literal_tuple(B) :- literal_tuple(B, _).
holdsIn(Atom, model(M), step(S1, S2)) :-
    step(S1, S2),  model(M), output(Atom, B), not occupied_literal_tuple(B).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/models.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Should be included everywhere
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

model(h;t).

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/all_1steps.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Calculates the maximum number of steps for fixpoint computation
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% We add +2 to offset the the final step not being allowed to be a fixpoint
step(0..N+2) :- #count{L: literal_tuple(_, L)} = N.

    
%!! Loaded from '/home/jesse/Documents/aftReified/modularized/axioms/all_2steps.lp'
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Included with all_1steps.lp to support nested iteration
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% We add +2 to offset the the final step not being allowed to be a fixpoint
step(S, 0..N+2) :- step(S), S > -1, #count{L: literal_tuple(_, L)} = N.

#show.
#show here(N) : #count{A : hold(A, model(h), step(S)), fp(model(h), step(S))} = N.
#show there(N) : #count{A : hold(A, model(t), step(S)), fp(model(t), step(S))} = N.