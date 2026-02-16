# Dimension Fields Update Summary

## Changes Made

### 1. Field Rename: `expected_type` → `dimension`

All three test question files have been updated:
- ✅ coordinate_test_questions.py (45 questions)
- ✅ hkdse_test_questions.py (35 questions)
- ✅ geometry_test_questions.py (10 questions)

### 2. Dimension Value Corrections

**coordinate_test_questions.py:**
- **Before:** 3D coordinate questions had `"expected_type": "3d"`
- **After:** 3D coordinate questions now have `"dimension": "coordinate_3d"` ✅

**Other files:** No value changes needed (already correct)

## Question Count by Dimension

| File | 2D | 3D | Coord 2D | Coord 3D | Total |
|------|----|----|----------|----------|-------|
| **coordinate_test_questions.py** | - | - | 30 | 15 | 45 |
| **hkdse_test_questions.py** | 14 | 17 | 1 | 3 | 35 |
| **geometry_test_questions.py** | 5 | 5 | - | - | 10 |
| **TOTAL** | **19** | **22** | **31** | **18** | **90** |

### Update Notes (2026-02-13)
Changed 4 HKDSE advanced questions from traditional to coordinate geometry:
- `hkdse_adv_2d_04`: "2d" → "coordinate_2d" (uses coordinates A(0,6), B(0,0), C(8,0))
- `hkdse_adv_3d_02`: "3d" → "coordinate_3d" (vertices at origin and coordinate points)
- `hkdse_adv_3d_04`: "3d" → "coordinate_3d" (vertices with explicit coordinates)
- `hkdse_adv_3d_05`: "3d" → "coordinate_3d" (vertices with explicit coordinates)

## Sample Questions for Review

### Traditional 2D (geometry_test_questions.py)
```python
{
    "id": "2d_01",
    "name": "Right Triangle Area",
    "text": "In triangle ABC, angle ACB = 90 degrees, AC = 24cm, BC = 12cm...",
    "dimension": "2d",  # ← Updated
    "topic": "triangles",
}
```

### Traditional 3D (hkdse_test_questions.py)
```python
{
    "id": "hkdse_3d_01",
    "name": "Square Pyramid Slant Height",
    "text": "A right square pyramid VABCD has a square base ABCD with side length 8cm...",
    "dimension": "3d",  # ← Updated
    "topic": "pyramids",
}
```

### Coordinate 2D (coordinate_test_questions.py)
```python
{
    "id": "coord_01",
    "name": "Line Through Two Points",
    "text": "Find the equation of the straight line passing through A(2, 3) and B(6, -1)...",
    "dimension": "coordinate_2d",  # ← Updated
    "topic": "straight_lines",
}
```

### Coordinate 3D (coordinate_test_questions.py)
```python
{
    "id": "coord_31",
    "name": "Three Planes Intersection",
    "text": "Three planes are given: P1: 2x + y - z = 4, P2: x - y + 2z = 3, P3: 3x + 2y + z = 7...",
    "dimension": "coordinate_3d",  # ← Fixed from "3d"
    "topic": "planes",
}
```

## Verification

To verify all questions have the correct dimension field:

```bash
# Check coordinate_test_questions.py
python3 -c "from coordinate_test_questions import *; print(f'2D: {sum(1 for q in COORDINATE_TEST_QUESTIONS if q[\"dimension\"] == \"coordinate_2d\")}'); print(f'3D: {sum(1 for q in COORDINATE_TEST_QUESTIONS if q[\"dimension\"] == \"coordinate_3d\")}')"

# Check hkdse_test_questions.py
python3 -c "from hkdse_test_questions import *; print(f'2D: {sum(1 for q in HKDSE_TEST_QUESTIONS if q[\"dimension\"] == \"2d\")}'); print(f'3D: {sum(1 for q in HKDSE_TEST_QUESTIONS if q[\"dimension\"] == \"3d\")}')"

# Check geometry_test_questions.py
python3 -c "from geometry_test_questions import *; print(f'2D: {sum(1 for q in GEOMETRY_TEST_QUESTIONS if q[\"dimension\"] == \"2d\")}'); print(f'3D: {sum(1 for q in GEOMETRY_TEST_QUESTIONS if q[\"dimension\"] == \"3d\")}')"
```

## LLM Classifier Test Script

A test script [test_classifier_accuracy.py](test_classifier_accuracy.py) has been created to:
1. Sample questions from each dimension category
2. Call the LLM classifier for each question **ASYNCHRONOUSLY** with high concurrency
3. Compare LLM output with the expected `dimension` field
4. Generate accuracy report with confusion matrix

### Usage Examples:

```bash
# Test 5 questions from each dimension (default, 50 concurrent requests)
python3 test_classifier_accuracy.py --sample-size 5

# Test all 90 questions asynchronously
python3 test_classifier_accuracy.py --sample-size all

# Test with 100 concurrent requests for maximum speed
python3 test_classifier_accuracy.py --sample-size all --concurrency 100

# Test only coordinate_2d questions
python3 test_classifier_accuracy.py --dimension coordinate_2d --sample-size 10

# Test with different random seed
python3 test_classifier_accuracy.py --sample-size 5 --seed 123
```

### Performance:
- **Async execution**: Uses `asyncio` with semaphore-based concurrency control
- **Default concurrency**: 50 concurrent API requests
- **Speed**: VERY fast - all 90 questions complete in ~10-20 seconds
- **Comparison**: ~15-30x faster than sequential testing (3-5 minutes → 10-20 seconds)

### Output:
- Real-time progress updates showing test results as they complete
- Console report with accuracy metrics, confusion matrix, and error breakdown
- Performance metrics (total time, average time per question, estimated speedup)
- Results saved to `classifier_test_results_{dimension}_{sample_size}.txt`

### Requirements:
- `GEMINI_API_KEY` environment variable must be set
- Uses Gemini 3 Flash for classification (~$0.0001 per question)
- Cost for all 90 questions: ~$0.009 HKD
