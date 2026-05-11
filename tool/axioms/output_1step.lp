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
