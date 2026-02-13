# Blueprint Generation Method Comparison

## Test Configuration
- **Total Questions**: 35
- **Date**: 2026-02-13 09:18:04

## Success Rate

| Method | Success | Failure | Rate |
|--------|---------|---------|------|
| Compact JSON | 35 | 0 | 100.0% |
| Structured Output | 35 | 0 | 100.0% |

## Token Usage

| Method | Total Tokens | Input Tokens | Output Tokens | Avg per Question |
|--------|--------------|--------------|---------------|------------------|
| Compact JSON | 235,375 | 28,988 | 20,308 | 6725 |
| Structured Output | 298,901 | 16,003 | 14,000 | 8540 |
| **Difference** | **+63,526** | -12,985 | -6,308 | +1815 |

## Cost Analysis

| Method | Total Cost | Cost per Question | Cost per Successful |
|--------|------------|-------------------|---------------------|
| Compact JSON | $0.0754 | $0.0022 | $0.0022 |
| Structured Output | $0.0500 | $0.0014 | $0.0014 |
| **Difference** | **$-0.0254** | **$-0.0007** | - |

## Performance

| Method | Avg Duration | Total Time |
|--------|--------------|------------|
| Compact JSON | 33.66s | 1178.0s |
| Structured Output | 45.34s | 1586.7s |
| **Difference** | **+11.68s** | **+408.7s** |

## Dimension Detection Accuracy

- **Matching dimensions**: 34/35 (97.1%)

### Dimension Mismatches

- **Orthocenter and Circumcenter**: Compact=2d, Structured=coordinate_2d

## Detailed Results

| Question | Compact | Structured | Token Diff | Cost Diff |
|----------|---------|------------|------------|----------|
| Cyclic Quadrilateral Angles | ✓ | ✓ | +1,049 | $-0.0007 |
| Tangent-Chord Angle | ✓ | ✓ | +283 | $-0.0010 |
| Two Tangents from External Point | ✓ | ✓ | -2,219 | $-0.0009 |
| Similar Triangles Ratio | ✓ | ✓ | +2,970 | $-0.0007 |
| Altitude and Similar Triangles | ✓ | ✓ | +402 | $-0.0007 |
| Cosine Rule Application | ✓ | ✓ | -1,651 | $+0.0001 |
| Sine Rule for Circumradius | ✓ | ✓ | +1,497 | $-0.0006 |
| Rhombus Diagonals | ✓ | ✓ | +1,759 | $-0.0007 |
| Trapezium Midsegment | ✓ | ✓ | +504 | $-0.0005 |
| Angle Bisector Theorem | ✓ | ✓ | +5,020 | $-0.0006 |
| Secants and Tangent from External Point | ✓ | ✓ | +937 | $-0.0007 |
| Incircle of Triangle | ✓ | ✓ | +5,397 | $-0.0006 |
| Power of a Point | ✓ | ✓ | +1,273 | $-0.0007 |
| Orthocenter and Circumcenter | ✓ | ✓ | +5,710 | $-0.0009 |
| Menelaus Theorem | ✓ | ✓ | +377 | $-0.0010 |
| Square Pyramid Slant Height | ✓ | ✓ | +436 | $-0.0011 |
| Triangular Pyramid Volume | ✓ | ✓ | +5,546 | $-0.0009 |
| Pyramid Angle with Base | ✓ | ✓ | +4,674 | $-0.0009 |
| Triangular Prism Diagonal | ✓ | ✓ | +4,434 | $-0.0008 |
| Cuboid Space Diagonal | ✓ | ✓ | -7,173 | $+0.0006 |
| Angle Between Line and Plane | ✓ | ✓ | +5,032 | $-0.0012 |
| Dihedral Angle in Pyramid | ✓ | ✓ | +1,605 | $-0.0007 |
| Distance from Point to Plane | ✓ | ✓ | +1,882 | $-0.0009 |
| Shortest Path on Surface | ✓ | ✓ | +2,110 | $-0.0011 |
| Cone Slant Height | ✓ | ✓ | +3,659 | $-0.0008 |
| Tetrahedron with Perpendicular Edges | ✓ | ✓ | +4,895 | $-0.0009 |
| Plane Equation and Distance | ✓ | ✓ | +3,432 | $-0.0007 |
| Angle Between Two Planes | ✓ | ✓ | +3,297 | $-0.0008 |
| Perpendicular from Vertex to Opposite Edge | ✓ | ✓ | +2,622 | $-0.0008 |
| Midpoint Plane in Prism | ✓ | ✓ | -112 | $+0.0006 |
| Cross Section of Pyramid | ✓ | ✓ | +192 | $-0.0010 |
| Shortest Distance Between Skew Lines | ✓ | ✓ | -628 | $-0.0010 |
| Angle Between Face Diagonal and Space Diagonal | ✓ | ✓ | -698 | $-0.0012 |
| Circumsphere of Tetrahedron | ✓ | ✓ | +3,565 | $-0.0006 |
| Projection onto Plane | ✓ | ✓ | +1,448 | $-0.0008 |
