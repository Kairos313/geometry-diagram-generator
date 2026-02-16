# Blueprint Generation Method Comparison

## Test Configuration
- **Total Questions**: 3
- **Date**: 2026-02-12 17:41:06

## Success Rate

| Method | Success | Failure | Rate |
|--------|---------|---------|------|
| Compact JSON | 3 | 0 | 100.0% |
| Structured Output | 0 | 3 | 0.0% |

## Token Usage

| Method | Total Tokens | Input Tokens | Output Tokens | Avg per Question |
|--------|--------------|--------------|---------------|------------------|
| Compact JSON | 20,448 | 2,460 | 1,626 | 6816 |
| Structured Output | 0 | 0 | 0 | 0 |
| **Difference** | **-20,448** | -2,460 | -1,626 | -6816 |

## Cost Analysis

| Method | Total Cost | Cost per Question | Cost per Successful |
|--------|------------|-------------------|---------------------|
| Compact JSON | $0.0061 | $0.0020 | $0.0020 |
| Structured Output | $0.0000 | $0.0000 | $0.0000 |
| **Difference** | **$-0.0061** | **$-0.0020** | - |

## Performance

| Method | Avg Duration | Total Time |
|--------|--------------|------------|
| Compact JSON | 32.54s | 97.6s |
| Structured Output | 0.00s | 0.0s |
| **Difference** | **-32.54s** | **-97.6s** |

## Dimension Detection Accuracy


## Detailed Results

| Question | Compact | Structured | Token Diff | Cost Diff |
|----------|---------|------------|------------|----------|
| Cyclic Quadrilateral Angles | ✓ | ✗ additionalProperties is not su | -8,206 | $-0.0020 |
| Tangent-Chord Angle | ✓ | ✗ additionalProperties is not su | -8,545 | $-0.0022 |
| Two Tangents from External Point | ✓ | ✗ additionalProperties is not su | -3,697 | $-0.0020 |

## Error Analysis

### Structured Output Errors (3)

- **Cyclic Quadrilateral Angles**: additionalProperties is not supported in the Gemini API.
- **Tangent-Chord Angle**: additionalProperties is not supported in the Gemini API.
- **Two Tangents from External Point**: additionalProperties is not supported in the Gemini API.
