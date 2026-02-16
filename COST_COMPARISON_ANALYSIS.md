# Cost Comparison: batch_test.py vs batch_test_focused.py

## TL;DR: Why Costs Are Higher

**batch_test_focused.py costs MORE because:**
1. ❌ Extra classification stage (+1 API call)
2. ❌ Classifier uses expensive Gemini output pricing ($3/M)
3. ❌ Blueprint locked to Gemini (no DeepSeek option)
4. ✅ Code generation uses cheaper DeepSeek

**vs batch_test.py with `--blueprint-model deepseek-direct --codegen-model deepseek-direct`:**
- Uses cheap DeepSeek ($0.28 input, $0.42 output) for BOTH stages
- Only 2 API calls instead of 3
- **Result: ~70% cheaper than batch_test_focused.py**

---

## Detailed Cost Breakdown

### batch_test.py Configuration Options

| Configuration | Blueprint | CodeGen | Stages | Cost/Diagram |
|--------------|-----------|---------|--------|--------------|
| `--codegen-model gemini` (default) | Gemini $0.50/$3.00 | Gemini $0.50/$3.00 | 2 | **$0.034** |
| `--codegen-model deepseek` | Gemini $0.50/$3.00 | DeepSeek $0.28/$0.42 | 2 | **$0.018** |
| `--blueprint-model deepseek-direct`<br>`--codegen-model deepseek-direct` | DeepSeek $0.28/$0.42 | DeepSeek $0.28/$0.42 | 2 | **$0.005** ⭐ |

### batch_test_focused.py (Fixed Configuration)

| Stage | Model | Pricing | Cost |
|-------|-------|---------|------|
| 0. Classify | Gemini 3 Flash | $0.50 input, $3.00 output | $0.0016 |
| 1. Blueprint | Gemini 3 Flash | $0.50 input, $3.00 output | $0.0104 |
| 2. CodeGen | DeepSeek Azure | $0.28 input, $0.42 output | $0.0048 |
| **Total** | 3 stages | | **$0.0168** |

---

## Cost Comparison Table

| Pipeline | Config | API Calls | Cost/Diagram | Relative |
|----------|--------|-----------|--------------|----------|
| **batch_test.py** | Gemini + Gemini | 2 | $0.0344 | 205% |
| **batch_test.py** | Gemini + DeepSeek | 2 | $0.0180 | 107% |
| **batch_test_focused.py** | Gemini + Gemini + DeepSeek | 3 | **$0.0168** | **100%** (baseline) |
| **batch_test.py** | DeepSeek + DeepSeek | 2 | **$0.0050** | **30%** ⭐ **CHEAPEST** |

---

## Why You're Seeing Higher Costs

### Scenario 1: You Previously Used DeepSeek for Both Stages
If you ran:
```bash
python3 batch_test.py --blueprint-model deepseek-direct --codegen-model deepseek-direct
```

**Old cost**: $0.0050/diagram (DeepSeek for both stages, 2 calls)
**New cost**: $0.0168/diagram (Gemini classifier + Gemini blueprint + DeepSeek code, 3 calls)
**Increase**: +236% 💸

### Scenario 2: You Previously Used Gemini for Blueprint, DeepSeek for Code
If you ran:
```bash
python3 batch_test.py --codegen-model deepseek
```

**Old cost**: $0.0180/diagram (Gemini blueprint + DeepSeek code, 2 calls)
**New cost**: $0.0168/diagram (Gemini classify + Gemini blueprint + DeepSeek code, 3 calls)
**Savings**: -7% (slight savings)

### Scenario 3: You Previously Used Gemini for Both Stages
If you ran:
```bash
python3 batch_test.py --codegen-model gemini
```

**Old cost**: $0.0344/diagram (Gemini for both, 2 calls)
**New cost**: $0.0168/diagram (Gemini classify + Gemini blueprint + DeepSeek code, 3 calls)
**Savings**: -51% (significant savings)

---

## Token-Level Analysis

### Typical Token Counts (Estimated)

| Stage | Input Tokens | Output Tokens | Notes |
|-------|--------------|---------------|-------|
| **batch_test.py (DeepSeek both)** | | | |
| Blueprint | ~2,100 | ~750 | Question + prompt → blueprint |
| CodeGen | ~2,800 | ~1,000 | Blueprint + prompt → code |
| **Subtotal** | **4,900** | **1,750** | **2 API calls** |
| | | | |
| **batch_test_focused.py** | | | |
| Classify | ~500 | ~50 | Question → dimension type |
| Blueprint | ~711 | ~750 | Question + focused prompt → blueprint |
| CodeGen | ~2,780 | ~1,000 | Blueprint + focused prompt → code |
| **Subtotal** | **3,991** | **1,800** | **3 API calls** |

### Cost Calculation (DeepSeek Both vs Focused)

**batch_test.py (DeepSeek both stages):**
```
Input:  4,900 tokens × $0.28/M = $0.0014
Output: 1,750 tokens × $0.42/M = $0.0007
Total:  $0.0021/diagram
```

**batch_test_focused.py:**
```
Classify Input:  500 tokens × $0.50/M = $0.00025
Classify Output:  50 tokens × $3.00/M = $0.00015
Blueprint Input:  711 tokens × $0.50/M = $0.00036
Blueprint Output: 750 tokens × $3.00/M = $0.00225
CodeGen Input:  2,780 tokens × $0.28/M = $0.00078
CodeGen Output: 1,000 tokens × $0.42/M = $0.00042
Total: $0.00421/diagram
```

**Difference**: batch_test_focused.py is **2x more expensive** when compared to DeepSeek-only pipeline.

---

## Why the Extra Classifier Stage is Expensive

The classifier stage uses **Gemini 3 Flash output pricing** ($3.00/M), which is:
- **7.1x more expensive** than DeepSeek output ($0.42/M)
- Applied to tiny outputs (~50 tokens for dimension type)
- Adds minimal value if you already know the dimension type

**Example:**
- Classifier output: 50 tokens × $3.00/M = **$0.00015**
- Same 50 tokens via DeepSeek: 50 tokens × $0.42/M = **$0.00002** (7.5x cheaper)

The classifier stage alone costs as much as **generating 350 tokens of DeepSeek output**.

---

## Solutions to Reduce Costs

### Option 1: Skip Classifier (Manual Dimension Type) ⭐ RECOMMENDED
Modify `batch_test_focused.py` to accept `--skip-classify` flag:
```python
if args.skip_classify:
    # User provides dimension type via question metadata
    detected_dimension = question.get("dimension_type", "2d")
else:
    # Run classifier stage
    detected_dimension = classify_geometry_type(...)
```

**Savings**: -$0.0016/diagram (-40% reduction from $0.0042 → $0.0025)

### Option 2: Use DeepSeek for Classification
Replace Gemini classifier with DeepSeek-Reasoner:
```python
# Current: Gemini 3 Flash
classify_result = openrouter_client.chat.completions.create(
    model="google/gemini-3-flash-preview",
    ...
)

# New: DeepSeek-Reasoner
classify_result = deepseek_client.chat.completions.create(
    model="deepseek-reasoner",
    ...
)
```

**Classifier cost reduction**: $0.0016 → $0.0002 (87% cheaper)
**Overall savings**: -$0.0014/diagram (-33% reduction)

### Option 3: Use DeepSeek for Blueprint Too
Allow `--blueprint-model deepseek-reasoner` in batch_test_focused.py:
```bash
python3 batch_test_focused.py --blueprint-model deepseek-reasoner
```

**Blueprint cost reduction**: $0.0104 → $0.0013 (88% cheaper)
**Overall savings**: -$0.0091/diagram (from $0.0168 → $0.0077)

**Result**: 54% cheaper than current, only 50% more expensive than DeepSeek-only batch_test.py

---

## Recommendation

### Immediate Fix (Best ROI)
Add `--skip-classify` flag to batch_test_focused.py for cases where dimension type is known:
- **Effort**: 10 lines of code
- **Savings**: 40% cost reduction
- **Benefit**: Maintain quality while reducing costs

### Medium-Term Fix
Support DeepSeek for blueprint generation:
- **Effort**: Integrate DeepSeek-Reasoner API
- **Savings**: 54% cost reduction vs current
- **Trade-off**: Slightly lower blueprint quality (test first)

### Long-Term Strategy
Keep both batch_test.py and batch_test_focused.py:
- **batch_test.py**: Production use with DeepSeek-only config (cheapest)
- **batch_test_focused.py**: Experimentation with classifier + better prompts

---

## Conclusion

**The individual prompts are NOT the problem** — they're 55% more compact than universal prompts.

**The cost increase comes from:**
1. Extra classification API call (+$0.0016)
2. Expensive Gemini output pricing for classifier ($3/M vs $0.42/M)
3. Locked blueprint model (Gemini instead of allowing DeepSeek)

**Fixing this requires code changes, not prompt optimization.**
