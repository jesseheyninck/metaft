%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Calculates the maximum number of steps for fixpoint computation
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% We add +2 to offset the the final step not being allowed to be a fixpoint
step(0..N+2) :- #count{L: literal_tuple(_, L)} = N.
