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
% However, we do not include the following converse because it can obscure/mask the source of derivation of atoms.
% We lose knowledge about which subset a fact was derived at
% hold(V, model(M), step(S1, S2)) :- step(S1, S2), hold(V, model(M), step(S1)).
