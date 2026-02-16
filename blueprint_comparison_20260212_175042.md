# Blueprint Generation Method Comparison

## Test Configuration
- **Total Questions**: 35
- **Date**: 2026-02-12 17:50:42

## Success Rate

| Method | Success | Failure | Rate |
|--------|---------|---------|------|
| Compact JSON | 35 | 0 | 100.0% |
| Structured Output | 35 | 0 | 100.0% |

## Token Usage

| Method | Total Tokens | Input Tokens | Output Tokens | Avg per Question |
|--------|--------------|--------------|---------------|------------------|
| Compact JSON | 259,887 | 28,988 | 20,214 | 7425 |
| Structured Output | 321,288 | 31,228 | 16,966 | 9180 |
| **Difference** | **+61,401** | +2,240 | -3,248 | +1754 |

## Cost Analysis

| Method | Total Cost | Cost per Question | Cost per Successful |
|--------|------------|-------------------|---------------------|
| Compact JSON | $0.0751 | $0.0021 | $0.0021 |
| Structured Output | $0.0665 | $0.0019 | $0.0019 |
| **Difference** | **$-0.0086** | **$-0.0002** | - |

## Performance

| Method | Avg Duration | Total Time |
|--------|--------------|------------|
| Compact JSON | 36.16s | 1265.7s |
| Structured Output | 48.56s | 1699.5s |
| **Difference** | **+12.39s** | **+433.8s** |

## Dimension Detection Accuracy

- **Matching dimensions**: 34/35 (97.1%)

### Dimension Mismatches

- **Orthocenter and Circumcenter**: Compact=2d, Structured=coordinate_2d

## Detailed Results

| Question | Compact | Structured | Token Diff | Cost Diff |
|----------|---------|------------|------------|----------|
| Cyclic Quadrilateral Angles | ✓ | ✓ | +3,492 | $-0.0006 |
| Tangent-Chord Angle | ✓ | ✓ | +871 | $-0.0004 |
| Two Tangents from External Point | ✓ | ✓ | +3,204 | $-0.0003 |
| Similar Triangles Ratio | ✓ | ✓ | +4,649 | $+0.0006 |
| Altitude and Similar Triangles | ✓ | ✓ | -92 | $-0.0004 |
| Cosine Rule Application | ✓ | ✓ | +1,532 | $-0.0005 |
| Sine Rule for Circumradius | ✓ | ✓ | +2,785 | $-0.0004 |
| Rhombus Diagonals | ✓ | ✓ | -6,682 | $+0.0008 |
| Trapezium Midsegment | ✓ | ✓ | +5,004 | $-0.0004 |
| Angle Bisector Theorem | ✓ | ✓ | +1,992 | $-0.0005 |
| Secants and Tangent from External Point | ✓ | ✓ | +1,619 | $+0.0005 |
| Incircle of Triangle | ✓ | ✓ | +5,473 | $-0.0003 |
| Power of a Point | ✓ | ✓ | +1,238 | $+0.0005 |
| Orthocenter and Circumcenter | ✓ | ✓ | -48 | $-0.0003 |
| Menelaus Theorem | ✓ | ✓ | +1,462 | $-0.0003 |
| Square Pyramid Slant Height | ✓ | ✓ | +1,712 | $-0.0007 |
| Triangular Pyramid Volume | ✓ | ✓ | +716 | $+0.0002 |
| Pyramid Angle with Base | ✓ | ✓ | -157 | $-0.0006 |
| Triangular Prism Diagonal | ✓ | ✓ | +4,586 | $+0.0009 |
| Cuboid Space Diagonal | ✓ | ✓ | +2,808 | $-0.0007 |
| Angle Between Line and Plane | ✓ | ✓ | +2,649 | $-0.0008 |
| Dihedral Angle in Pyramid | ✓ | ✓ | +1,938 | $-0.0007 |
| Distance from Point to Plane | ✓ | ✓ | +1,919 | $-0.0004 |
| Shortest Path on Surface | ✓ | ✓ | +1,669 | $-0.0008 |
| Cone Slant Height | ✓ | ✓ | +4,914 | $-0.0006 |
| Tetrahedron with Perpendicular Edges | ✓ | ✓ | +2,013 | $-0.0006 |
| Plane Equation and Distance | ✓ | ✓ | -4,886 | $+0.0007 |
| Angle Between Two Planes | ✓ | ✓ | +3,595 | $-0.0005 |
| Perpendicular from Vertex to Opposite Edge | ✓ | ✓ | +2,637 | $+0.0007 |
| Midpoint Plane in Prism | ✓ | ✓ | +1,314 | $+0.0008 |
| Cross Section of Pyramid | ✓ | ✓ | +1,084 | $-0.0007 |
| Shortest Distance Between Skew Lines | ✓ | ✓ | -199 | $-0.0008 |
| Angle Between Face Diagonal and Space Diagonal | ✓ | ✓ | +4,932 | $-0.0007 |
| Circumsphere of Tetrahedron | ✓ | ✓ | -127 | $-0.0005 |
| Projection onto Plane | ✓ | ✓ | +1,785 | $-0.0005 |
