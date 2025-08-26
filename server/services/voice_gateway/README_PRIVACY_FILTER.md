# Privacy Filter - Strict PII Removal for Voice Responses

A comprehensive privacy filter that converts raw LLM/tool results into safe, spoken summaries for TTS with zero PII leakage.

## Features

- **Strict PII Detection**: Detects and removes personal names, emails, phone numbers, addresses, SSNs, credit cards, exact numbers, and quoted content
- **TTS-Optimized Output**: Generates summaries optimized for spoken delivery (max 300 characters, natural flow)
- **Multi-Layer Validation**: Pattern-based detection + semantic validation + strict output verification
- **Comprehensive Fallback**: Intelligent fallback system when primary filtering fails
- **Audit Logging**: Complete audit trail for all filtering operations
- **Performance Metrics**: Real-time metrics tracking and performance monitoring
- **Test Suite**: Built-in test suite to validate PII filtering effectiveness

## Quick Start

```python
from privacy_filter import filter_for_tts, get_privacy_filter

# Simple usage - convert raw result to safe TTS summary
raw_result = "John Smith (john@company.com) called about the $50,000 contract."
safe_summary = await filter_for_tts(raw_result)
print(safe_summary)
# Output: "Someone called about the contract."

# Advanced usage with full control
privacy_filter = get_privacy_filter(max_summary_length=200)
result = await privacy_filter.filter_to_safe_summary(raw_result)
print(f"Safe: {result.safe_summary}")
print(f"PII Removed: {len(result.pii_matches)} items")
print(f"Filter Time: {result.filter_duration_ms:.1f}ms")
```

## Integration with Voice Gateway

The privacy filter is designed to integrate seamlessly with the voice gateway pipeline:

```python
# In your tool executor or LLM response handler
async def process_voice_response(raw_result: str) -> str:
    """Process raw result for voice output"""
    
    # Apply privacy filtering
    safe_summary = await filter_for_tts(raw_result, context={
        "user_session": session_id,
        "tool_type": "email_search"
    })
    
    # Send to TTS
    return safe_summary
```

## PII Detection Coverage

### Automatically Detected and Removed:
- **Person Names**: John Smith, Dr. Johnson, etc.
- **Email Addresses**: user@domain.com, name at company dot com
- **Phone Numbers**: (555) 123-4567, +1-555-123-4567, etc.
- **Addresses**: 123 Main St, Boston MA 02101
- **Social Security Numbers**: 123-45-6789
- **Credit Card Numbers**: 4532-1234-5678-9000
- **Exact Numbers**: Large numbers converted to approximations
- **URLs and File Paths**: https://example.com, /path/to/file
- **Quoted Content**: Long quoted text or excerpts
- **Account IDs**: ABC123456789, etc.

### Safe Replacements:
- Person names → "someone", "a person"  
- Emails → "an email address"
- Phone numbers → "a phone number"
- Large numbers → "thousands", "many thousands"
- Addresses → "an address", "a location"
- Quotes → "some content", "information"

## System Prompts

The filter uses carefully crafted system prompts for LLM-based filtering:

```
Rewrite the given raw_result into a 1-2 sentence spoken summary for TTS in English, 
removing PII and specifics. No names, emails, addresses, IDs, quotes, or exact figures 
beyond coarse counts.

Rules:
- Maximum 300 characters
- Use general terms: "someone", "a person", "the user", "several", "many", "around X"
- Remove all specific identifiers
- Convert exact numbers to approximate ranges
- Focus on the essence, not details
- Optimize for spoken delivery (natural, flowing language)
```

## Validation and Safety

### Multi-Layer Validation:
1. **Pattern-based Detection**: Regex patterns for known PII types
2. **Semantic Analysis**: Context-aware PII detection
3. **Output Validation**: Strict verification of filtered results
4. **Fallback Systems**: Emergency fallbacks when filtering fails

### Safety Guarantees:
- **Zero PII Leakage**: Strict validation blocks any PII in final output
- **Deploy Blocking**: System will refuse to deploy if PII is detected
- **Audit Trail**: Complete logging for security reviews
- **Emergency Fallback**: Safe generic responses when all else fails

## Testing

Run the built-in test suite:

```bash
# Run basic test suite
python3 privacy_filter.py

# Run integration tests
python3 test_privacy_filter_integration.py
```

### Test Coverage:
- Person name filtering
- Email address removal
- Phone number scrubbing
- Address anonymization
- Number generalization
- Quote/excerpt filtering
- Fallback scenarios
- Integration testing

## Performance

- **Filter Time**: Typically < 5ms per request
- **Memory Usage**: Minimal - stateless processing
- **Throughput**: Designed for real-time voice processing
- **Latency**: Optimized for voice interaction requirements

## Metrics and Monitoring

```python
# Get filtering metrics
metrics = privacy_filter.get_metrics()
print(f"Total filters: {metrics['total_filters']}")
print(f"PII detections: {metrics['pii_detections']}")
print(f"Avg filter time: {metrics['avg_filter_time_ms']:.1f}ms")

# Get audit log
audit_log = privacy_filter.get_audit_log(limit=100)
for entry in audit_log:
    print(f"Filter {entry['audit_id']}: {entry['pii_count']} PII items removed")
```

## Configuration

### Environment Variables:
- `PRIVACY_MAX_SUMMARY_LENGTH`: Maximum summary length (default: 300)
- `PRIVACY_STRICT_MODE`: Enable strictest filtering (default: true)
- `PRIVACY_AUDIT_ENABLED`: Enable audit logging (default: true)

### Customization:
```python
# Custom privacy filter with specific settings
privacy_filter = PrivacyFilter(
    max_summary_length=200  # Shorter summaries
)
```

## Error Handling

The privacy filter includes comprehensive error handling:

- **PIILeakageError**: Thrown when PII is detected in output
- **PrivacyFilterError**: General filtering errors
- **Emergency Fallback**: Safe generic responses for critical failures
- **Graceful Degradation**: System continues operating with reduced functionality

## Security Considerations

- **No Data Storage**: Filter doesn't store any input/output data
- **Hash-based Auditing**: Only hashes stored for audit purposes
- **Stateless Design**: No session data retention
- **Fail-Safe**: System fails to safe state, never leaks PII
- **Regular Updates**: PII patterns updated for new threats

## Integration Examples

### With LLM Stream:
```python
async def process_llm_response(llm_response: str) -> str:
    """Process LLM response for voice output"""
    return await filter_for_tts(llm_response)
```

### With Tool Executor:
```python
async def execute_tool_and_filter(tool_name: str, params: dict) -> str:
    """Execute tool and return filtered result"""
    raw_result = await execute_tool(tool_name, params)
    return await filter_for_tts(raw_result)
```

### With Voice Pipeline:
```python
async def voice_pipeline_filter(raw_input: str) -> str:
    """Filter raw input for voice pipeline"""
    privacy_filter = get_privacy_filter()
    result = await privacy_filter.filter_to_safe_summary(raw_input)
    
    if not result.validation_passed:
        raise PIILeakageError("PII validation failed")
    
    return result.safe_summary
```

## Maintenance

### Adding New PII Patterns:
1. Update pattern lists in `_init_pii_patterns()`
2. Add corresponding test cases
3. Update replacement logic
4. Run full test suite to validate

### Updating Replacements:
1. Modify `_generalize_number()` for number replacements
2. Update `PIIMatch.replacement` values
3. Test with realistic scenarios

### Performance Tuning:
1. Profile with realistic data volumes
2. Optimize regex patterns for speed
3. Adjust batch processing if needed
4. Monitor memory usage patterns

## Support

For issues or questions:
1. Check test suite results first
2. Review audit logs for filtering behavior
3. Test with minimal reproduction case
4. Check metrics for performance issues

The privacy filter is designed to be bulletproof for production voice systems while maintaining high performance and usability.