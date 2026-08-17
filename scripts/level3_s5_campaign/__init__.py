"""Level3 S5 campaign infrastructure (lot L3-P). Deliberately isolated
from scripts.level3_campaign (the S4 campaign layer, lot L3-I): no
runtime import of that package from here, even though several primitives
(git provenance, atomic JSON writes) are structurally identical -- the S4
campaign layer and its frozen contract stay untouched and independently
reviewable."""
