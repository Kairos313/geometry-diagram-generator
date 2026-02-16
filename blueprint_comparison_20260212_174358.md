# Blueprint Generation Method Comparison

## Test Configuration
- **Total Questions**: 3
- **Date**: 2026-02-12 17:43:58

## Success Rate

| Method | Success | Failure | Rate |
|--------|---------|---------|------|
| Compact JSON | 3 | 0 | 100.0% |
| Structured Output | 3 | 0 | 100.0% |

## Token Usage

| Method | Total Tokens | Input Tokens | Output Tokens | Avg per Question |
|--------|--------------|--------------|---------------|------------------|
| Compact JSON | 23,053 | 2,460 | 1,554 | 7684 |
| Structured Output | 23,521 | 2,652 | 1,338 | 7840 |
| **Difference** | **+468** | +192 | -216 | +156 |

## Cost Analysis

| Method | Total Cost | Cost per Question | Cost per Successful |
|--------|------------|-------------------|---------------------|
| Compact JSON | $0.0059 | $0.0020 | $0.0020 |
| Structured Output | $0.0053 | $0.0018 | $0.0018 |
| **Difference** | **$-0.0006** | **$-0.0002** | - |

## Performance

| Method | Avg Duration | Total Time |
|--------|--------------|------------|
| Compact JSON | 37.14s | 111.4s |
| Structured Output | 39.33s | 118.0s |
| **Difference** | **+2.18s** | **+6.5s** |

## Dimension Detection Accuracy

- **Matching dimensions**: 3/3 (100.0%)


## Detailed Results

| Question | Compact | Structured | Token Diff | Cost Diff |
|----------|---------|------------|------------|----------|
| Cyclic Quadrilateral Angles | ✓ | ✓ | +971 | $-0.0004 |
| Tangent-Chord Angle | ✓ | ✓ | -3,527 | $+0.0004 |
| Two Tangents from External Point | ✓ | ✓ | +3,024 | $-0.0006 |
