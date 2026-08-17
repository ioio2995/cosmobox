"""Level3 S7 campaign infrastructure (lot L3-AC). Deliberately isolated
from scripts.level3_campaign (the S4 campaign layer, lot L3-I),
scripts.level3_s5_campaign (the S5 campaign layer, lot L3-P), and
scripts.level3_s6_campaign (the S6 campaign layer, lot L3-W): no runtime
import of any of those packages from here, even though several
primitives (git provenance, atomic JSON writes) are structurally
identical -- the S4, S5, and S6 campaign layers and their frozen
contracts stay untouched and independently reviewable."""
