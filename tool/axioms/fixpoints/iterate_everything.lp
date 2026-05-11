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
