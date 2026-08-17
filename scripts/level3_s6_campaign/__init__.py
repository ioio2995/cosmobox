"""Level3 S6 campaign infrastructure (lot L3-W). Deliberately isolated
from scripts.level3_campaign (the S4 campaign layer, lot L3-I) and
scripts.level3_s5_campaign (the S5 campaign layer, lot L3-P): no runtime
import of either package from here, even though several primitives (git
provenance, atomic JSON writes) are structurally identical -- the S4 and
S5 campaign layers and their frozen contracts stay untouched and
independently reviewable."""
