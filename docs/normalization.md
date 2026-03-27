# Normalization

## Goal

Map noisy receipt line items into cleaner product names and coarse categories without pretending the model is fully correct.

## Early approach

- use explicit rules for known patterns
- preserve raw text alongside normalized output
- keep categories low-cardinality and explainable

## Evolution path

- add merchant-aware rules
- track confidence and unmatched cases
- layer product identity over simple string rules
