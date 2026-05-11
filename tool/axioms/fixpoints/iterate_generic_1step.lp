%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Removes inconsistent assignments and constrains to look for
% fixpoints
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% What's true here, is true there as well. 
hold(L, model(t), step(I)) :- hold(L, model(h), step(I)).

% Discard answer sets that aren't fixpoints
fp(model(M)) :- fp(model(M), step(_)).
:- not fp(model(M)), model(M).
