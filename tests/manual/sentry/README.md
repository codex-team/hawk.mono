# Installation

```
pip install sentry-sdk
```

# Message structure

A Sentry envelope is typically a structured format consisting of multiple JSON parts concatenated together. It starts with a header, followed by one or more items separated by **newlines**, with each item having its own header and body.

## Structure of a Sentry Envelope
1. Envelope Header (JSON): Describes the envelope metadata (e.g., dsn, event_id).
2. Item Header (JSON): Precedes each item, describing its type (e.g., event, transaction) and optional metadata like length.
3. Item Payload (Optional JSON): The actual data of the item.

Example Sentry Envelope:
```{"event_id":"1234", "dsn":"https://example.com"}
{"type":"event", "length":30}
{"key":"value"}
{"type":"attachment", "length":14}
"sample-attachment"
```

## Structure parser
```
type SentryEnvelope struct {
	Header map[string]interface{}
	Items  []SentryItem
}
type SentryItem struct {
	Header  map[string]interface{}
	Payload map[string]interface{}
}

func parseSentryEnvelope(data string, envelope *SentryEnvelope) error {
	scanner := bufio.NewScanner(strings.NewReader(data))
	scanner.Split(bufio.ScanLines)

	// Parse the envelope header
	if !scanner.Scan() {
		return fmt.Errorf("failed to read envelope header")
	}
	envelopeHeader := scanner.Text()
	envelope.Header = make(map[string]interface{})
	if err := json.Unmarshal([]byte(envelopeHeader), &envelope.Header); err != nil {
		return fmt.Errorf("failed to parse envelope header: %w", err)
	}

	// Parse each item
	for scanner.Scan() {
		itemHeader := scanner.Text()
		var item SentryItem
		item.Header = make(map[string]interface{})
		if err := json.Unmarshal([]byte(itemHeader), &item.Header); err != nil {
			return fmt.Errorf("failed to parse item header: %w", err)
		}

		// Parse the item payload
		if scanner.Scan() {
			itemPayload := scanner.Text()
			item.Payload = make(map[string]interface{})

			if err := json.Unmarshal([]byte(itemPayload), &item.Payload); err != nil {
				return fmt.Errorf("failed to parse item payload: %w", err)
			}
		}
		envelope.Items = append(envelope.Items, item)
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("error reading envelope: %w", err)
	}

	return nil
}
```
can be used as:
```
var envelope SentryEnvelope
err = parseSentryEnvelope(jsonBody, &envelope)
if err != nil {
    log.Warnf("Failed to parse Sentry envelope: %s", err)
    sendAnswerHTTP(ctx, ResponseMessage{Code: 400, Error: true, Message: "Failed to parse Sentry envelope"})
    return
}
```