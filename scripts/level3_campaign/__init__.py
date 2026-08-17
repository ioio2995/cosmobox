"""Level3 S4 campaign infrastructure (lot L3-I). Deliberately isolated from
scripts.level2_campaign: no runtime import of that package from here, even
though several primitives (git provenance, atomic JSON writes) are
structurally identical -- Level2's campaign layer stays untouched and
independently reviewable."""
