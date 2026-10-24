# Dark Pattern Detector — API Contract

## Audit Result Format

Every audit should return a JSON object in this format:

```json
{
  "audit_id": "abc123",
  "url": "https://example.com/product/1",
  "site": "example.com",
  "status": "completed",
  "findings": [
    {
      "pattern": "fake_urgency",
      "detected": true,
      "evidence_text": "Countdown timer resets after refreshing the page",
      "screenshot": "samples/abc123_timer.png",
      "legal_category": "False urgency",
      "severity": 7
    }
  ],
  "total_score": 18
}
```

## Field Definitions

- `audit_id`: Unique identifier for the audit.
- `url`: URL being audited.
- `site`: Website domain.
- `status`: Audit status, such as `running`, `completed`, or `failed`.
- `findings`: List of detected dark patterns.
- `pattern`: Pattern identifier, such as `hidden_fees`, `fake_urgency`, or `false_scarcity`.
- `detected`: Whether the pattern was detected.
- `evidence_text`: Text or observation supporting the finding.
- `screenshot`: Path to supporting evidence, when available.
- `legal_category`: Applicable dark-pattern category.
- `severity`: Severity score assigned by the classification system.
- `total_score`: Combined score for the audit.

All team members should follow this contract when implementing their components.