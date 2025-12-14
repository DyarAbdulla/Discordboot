# Memory Decay and Importance Scoring

## Overview

The memory system now includes **intelligent decay** and **importance scoring** to ensure critical information (like user preferences) persists longer while less important memories fade or merge over time.

## Features

### 1. ✅ Importance Scoring

**File: `utils/importance_scorer.py`**

Messages and summaries are automatically scored based on:
- **User Preferences** (+0.3 score): Keywords like "prefer", "like", "favorite", "my name is"
- **Critical Information** (+0.4 score): Keywords like "important", "remember", "critical", "allergy"
- **Questions** (+0.1 score): User seeking help
- **Message Length** (+0.05): Longer messages may be more detailed

**Score Range:** 0.0 to 1.0 (higher = more important)

### 2. ✅ Memory Decay

**Decay Rates Based on Importance:**

- **Critical Info (score > 0.8)**: 
  - 0.5% decay per day if accessed recently
  - 1% decay per day if not accessed in 30+ days
  - Persists much longer

- **Important Info (score > 0.6)**:
  - 2% decay per day
  - Normal decay rate

- **Normal Info (score ≤ 0.6)**:
  - 3% decay per day
  - Faster decay

**Decay Formula:**
```
decayed_score = importance_score - (age_days * decay_rate)
```

### 3. ✅ Automatic Summary Merging

**When:** Summaries older than 90 days with importance < 0.3

**Process:**
1. Group adjacent summaries by time period
2. Merge multiple summaries into one
3. Average importance scores (slightly reduced)
4. Delete old summaries, insert merged summary

**Benefits:**
- Reduces database size
- Preserves context
- Keeps important information accessible

### 4. ✅ Automatic Summary Dropping

**When:** Summaries with decayed score < 0.2

**Process:**
1. Calculate decay-adjusted score
2. Drop summaries below threshold
3. Keep important summaries indefinitely

**Critical Preferences:**
- User preferences (score > 0.7) persist much longer
- Critical info (score > 0.8) rarely drops
- Only very old, low-importance summaries are removed

## Database Schema Updates

### `conversations` Table
```sql
ALTER TABLE conversations ADD COLUMN importance_score REAL DEFAULT 0.5;
ALTER TABLE conversations ADD COLUMN last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP;
```

### `summaries` Table
```sql
ALTER TABLE summaries ADD COLUMN importance_score REAL DEFAULT 0.5;
ALTER TABLE summaries ADD COLUMN last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP;
```

## How It Works

### Message Storage
1. User sends message → Importance score calculated automatically
2. Message stored with score → Higher scores persist longer
3. Preferences detected → Extra importance boost

### Summary Creation
1. Old messages summarized → Importance score calculated
2. Preferences extracted → Added to summary text
3. Summary stored with score → Critical info persists

### Memory Retrieval
1. Load summaries → Apply decay based on age
2. Filter by importance → Only include scores > 0.2
3. Sort by decayed score → Most important first
4. Limit to top 10 → Prevents overflow

### Background Cleanup (Every Hour)
1. Find old summaries (>90 days)
2. Calculate decay scores
3. Merge low-importance summaries
4. Drop very low scores (<0.2)
5. Clean old messages (keep important ones)

## Example Scenarios

### Scenario 1: User Preference
```
User: "I prefer Python over JavaScript"
Score: 0.8 (preference detected)
Decay: 0.5% per day
Lifespan: ~200 days before significant decay
```

### Scenario 2: Critical Information
```
User: "I'm allergic to peanuts - remember this!"
Score: 0.9 (critical keyword detected)
Decay: 0.5% per day
Lifespan: ~180 days, persists much longer
```

### Scenario 3: Normal Conversation
```
User: "How's the weather?"
Score: 0.5 (normal conversation)
Decay: 3% per day
Lifespan: ~17 days before dropping below threshold
```

### Scenario 4: Summary Merging
```
3 summaries, each 100 days old, scores: 0.4, 0.35, 0.3
→ Merged into 1 summary
→ Average score: 0.35 → Reduced to 0.28
→ Saves space, preserves context
```

## Configuration

No configuration needed - works automatically with sensible defaults:
- **Decay threshold**: 0.2 (summaries below this are dropped)
- **Merge threshold**: 0.3 (summaries below this are merged)
- **Max age for merging**: 90 days
- **Cleanup interval**: Every hour

## Benefits

✅ **Critical Info Persists**: User preferences and important info last much longer  
✅ **Automatic Cleanup**: Old, unimportant memories fade away  
✅ **Efficient Storage**: Merging reduces database size  
✅ **Smart Prioritization**: Important summaries loaded first  
✅ **No Manual Intervention**: Everything happens automatically  

## API Changes

### `MemoryManager.add_message()`
- Now accepts optional `importance_score` parameter
- Auto-calculates if not provided

### `MemoryManager.create_summary()`
- Now accepts optional `importance_score` parameter
- Auto-calculates if not provided

### `MemoryManager.get_conversation_context()`
- Now accepts `min_importance` parameter (default: 0.2)
- Returns only summaries above threshold
- Applies decay automatically

### `MemoryManager.merge_old_summaries()`
- New method to merge/drop old summaries
- Called automatically by background task

## Testing

```python
from utils.importance_scorer import ImportanceScorer
from utils.memory_manager import MemoryManager

# Test importance scoring
message = {"role": "user", "content": "I prefer Python programming"}
score = ImportanceScorer.score_message(message)
print(f"Importance score: {score}")  # Should be ~0.8

# Test memory decay
mm = MemoryManager()
decayed = mm._calculate_decay_score(0.8, age_days=30, last_accessed_days=5)
print(f"Decayed score: {decayed}")  # Should be ~0.75

# Test summary merging
merged = mm.merge_old_summaries("user123", "channel456", max_age_days=90)
print(f"Merged {merged} summaries")
```

## Files Changed

1. **`utils/importance_scorer.py`** (NEW)
   - Importance scoring logic
   - Preference extraction
   - Critical keyword detection

2. **`utils/memory_manager.py`** (UPDATED)
   - Added importance_score columns
   - Added last_accessed tracking
   - Added decay calculation
   - Added merge/drop methods
   - Updated context retrieval with decay

3. **`bot.py`** (UPDATED)
   - Background task for memory decay
   - Preference extraction during summarization
   - Importance score calculation

