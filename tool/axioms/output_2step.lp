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
