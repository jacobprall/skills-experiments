# Trial Report: mask_001

- **Agent:** sage
- **Plugin Set:** none
- **Model:** default
- **Run ID:** 20260226_165533_787445
- **Started:** 2026-02-26T16:55:33.741811
- **Duration:** 28.1s

---

## Overall: PASSED

- **Score:** 5.0/5.0 (100%)

## Requirements (Gates)

| Requirement | Status | Details |
|---|---|---|
| ssn_has_masking_policy | PASS | {'CT': 1} |
| policy_has_mask_pattern | PASS | {'HAS_MASK': 1} |

## Assertions (Points)

| Assertion | Category | Type | Points | Details |
|---|---|---|---|---|
| policy_in_governance_schema | governance | sql | 2.0/2.0 | {'CT': 1} |
| policy_correct_return_type | governance | sql | 1.0/1.0 | {'CORRECT_TYPE': 1} |
| admin_sees_cleartext | governance | sql | 2.0/2.0 | {'ADMIN_EXEMPT': 1} |
| **Total** | | | **5.0/5.0** | |

## Transcript

Full transcript: `/Users/jprall/Desktop/skills_benchmark/results/20260226_165533_787445/mask_001/transcript.jsonl`
