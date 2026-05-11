%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Included with all_1steps.lp to support nested iteration
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% We add +2 to offset the the final step not being allowed to be a fixpoint
step(S, 0..N+2) :- step(S), S > -1, #count{L: literal_tuple(_, L)} = N.
