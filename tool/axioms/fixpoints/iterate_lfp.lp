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
