# 💬 Chat Interface Guide

## Quick Start

### 1. Start the FALM Server

```bash
python main.py
```

The API will start on `http://localhost:8000`

### 2. Open the Chat Interface

Open [chat_interface.html](chat_interface.html) in your web browser:

```bash
# macOS
open chat_interface.html

# Linux
xdg-open chat_interface.html

# Windows
start chat_interface.html
```

### 3. Start Searching!

Try these example queries:
- "Find innovation grants for AI startups"
- "Show me clean energy funding opportunities"
- "What grants are available for SMEs?"
- "Healthcare innovation grants with match funding"

## Features

### 🔍 Smart Search
- **Semantic Search**: Understands meaning, not just keywords
- **Keyword Matching**: Also searches for exact terms
- **Hybrid Scoring**: 70% semantic + 30% keyword relevance

### 📊 Rich Grant Display

Each grant card shows:
- **Title & Description**: Full grant overview
- **Relevance Score**: % match to your query
- **Funding Amount**: Min/max amounts with currency
- **Deadline**: Application closing date
- **Funding Body**: Innovate UK, Horizon Europe, etc.
- **Match Funding**: Whether co-funding is required

### 🎯 Expandable Details

Click "Show Details" to see:
- ✅ **Eligibility Criteria**: Who can apply
- 🎯 **Scope**: What projects are eligible
- 📋 **How to Apply**: Application process

### 🔗 Quick Actions
- **View Full Details**: Opens official grant page
- **Apply Now**: Direct link to application portal

## Current Data

The chat interface connects to your ChromaDB Cloud database with:

- **29 Innovate UK grants** fully enriched
- All 6 sections scraped per grant:
  - Summary
  - Eligibility
  - Scope
  - Dates
  - How to Apply
  - Supporting Information

## Search Tips

### By Sector
```
"quantum computing grants"
"healthcare AI funding"
"clean energy innovation"
```

### By Amount
```
"grants under £500k"
"funding over £1M"
"small business grants"
```

### By Eligibility
```
"SME grants for UK companies"
"startup funding opportunities"
"university research grants"
```

### By Deadline
```
"grants closing soon"
"funding available in 2025"
"applications due this month"
```

## Technical Details

### API Endpoints Used

**Query Endpoint**:
```javascript
POST http://localhost:8000/api/query

Body:
{
  "query": "your search query",
  "max_results": 10
}

Response:
{
  "total_results": 5,
  "grants": [...],
  "nlms_queried": ["innovate_uk", "horizon_europe"],
  "processing_time_ms": 234,
  "sme_context": "Tips for SMEs..."
}
```

**Health Check**:
```javascript
GET http://localhost:8000/health
```

### Grant Data Structure

Each grant returned includes:
```json
{
  "grant_id": "IUK_2313",
  "title": "Smart Grants: Spring 2025",
  "description": "Support for game-changing innovation...",
  "relevance_score": 0.87,
  "semantic_score": 0.85,
  "keyword_score": 0.92,
  "funding_body": "Innovate UK",
  "amount_min": 25000,
  "amount_max": 2000000,
  "currency": "GBP",
  "deadline": "{'competition_opens': '27 November 2025'}",
  "match_funding_required": true,
  "eligibility": "UK registered business, TRL 4-8...",
  "scope": "Projects must demonstrate innovation...",
  "application_process": "Apply via IFS portal...",
  "source_url": "https://apply-for-innovation-funding...",
  "domain": "innovate_uk"
}
```

## Customization

### Change API URL

Edit line 472 in `chat_interface.html`:

```javascript
const API_URL = 'http://localhost:8000';
```

### Adjust Max Results

Edit line 708 in `chat_interface.html`:

```javascript
body: JSON.stringify({
    query: query,
    max_results: 10  // Change this number
})
```

### Modify Suggestions

Edit the suggestion chips (lines 439-442):

```html
<div class="suggestion-chip" onclick="sendSuggestion('Your custom query')">
    🔥 Your Label
</div>
```

## Troubleshooting

### "Connection Error" Message

**Problem**: Can't connect to the API

**Solutions**:
1. Make sure the server is running: `python main.py`
2. Check the server is on port 8000
3. Look for errors in the server console
4. Verify ChromaDB Cloud connection is active

### No Results Found

**Problem**: Query returns 0 grants

**Solutions**:
1. Try broader search terms
2. Check grants are loaded: `python scripts/test_chromadb_connection.py`
3. Verify grants match your query
4. Try example queries from the suggestions

### Grants Missing Details

**Problem**: Eligibility/scope sections are empty

**This is expected** - not all grants have been fully enriched yet. Only grants scraped with `scrape_full_iuk_grants.py` will have complete details.

To enrich more grants:
```bash
# Re-scrape with full details
python scripts/scrape_full_iuk_grants.py

# Reload to ChromaDB
python scripts/load_enriched_grants.py
```

## Performance

- **Average query time**: 200-500ms
- **Hybrid search**: 70% semantic + 30% keyword
- **Caching**: 1-hour TTL for repeated queries
- **Batch processing**: Optimized for speed

## Browser Compatibility

Works in all modern browsers:
- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Opera

Requires JavaScript enabled.

## Next Steps

1. **Test the interface**: Try various queries
2. **Add more grants**: Load additional data sources
3. **Customize styling**: Edit CSS in chat_interface.html
4. **Deploy**: Host on a web server for remote access

## Support

For issues or questions:
- Check the [main README](README.md)
- Review [SYSTEM_READY.md](SYSTEM_READY.md)
- See [LOADING_GRANTS_GUIDE.md](LOADING_GRANTS_GUIDE.md)

---

**Happy Grant Hunting!** 🎯
