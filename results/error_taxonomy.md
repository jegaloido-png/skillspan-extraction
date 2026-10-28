Error taxonomy on test (mean over seeds for BERT/JobBERT). Predicted spans are split into exact, boundary errors (`shorter` = prediction inside a gold span, `longer` = prediction contains a gold span, `shifted` = partial overlap) and `spurious` (no overlap). Gold spans: `missed` (no overlapping prediction) or `gold_boundary_only` (overlapped but never exact).

### Skill (all sources)

| system | gold | pred | exact | shorter | longer | shifted | spurious | gold missed | gold boundary-only |
|---|---|---|---|---|---|---|---|---|---|
| dictionary | 1091 | 448 | 124 | 87 | 14 | 1 | 222 | 868 | 99 |
| bert | 1091 | 1086 | 521 | 188 | 118 | 8 | 251 | 262 | 309 |
| jobbert | 1091 | 1140 | 578 | 201 | 116 | 5 | 239 | 210 | 303 |

### Knowledge (all sources)

| system | gold | pred | exact | shorter | longer | shifted | spurious | gold missed | gold boundary-only |
|---|---|---|---|---|---|---|---|---|---|
| dictionary | 1174 | 1030 | 560 | 95 | 17 | 1 | 357 | 499 | 115 |
| bert | 1174 | 1352 | 822 | 146 | 70 | 5 | 308 | 149 | 202 |
| jobbert | 1174 | 1365 | 854 | 163 | 62 | 5 | 282 | 126 | 194 |
