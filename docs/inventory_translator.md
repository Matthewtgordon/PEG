# Inventory Translator - Natural Language to InventoryCommand

## Overview

The Inventory Translator is a natural language processing module that converts plain English inventory requests into structured `InventoryCommand` dictionaries that can be executed by the Shopify Inventory Service.

**Location**: `src/apeg_core/translators/inventory_text_to_command.py`

## Features

- 🗣️ **Natural Language Processing**: Uses OpenAI GPT-4o-mini to understand inventory requests
- 📋 **Structured Output**: Generates valid `InventoryCommand` dictionaries
- 🔄 **CLI Interface**: Interactive and stdin-based command-line tool
- ✅ **Validation**: Automatically validates command structure
- 📊 **Human-Readable Results**: Formats execution results for easy reading

## Architecture

```
User Input (Natural Language)
       ↓
OpenAI GPT-4o-mini (Translation)
       ↓
InventoryCommand (JSON)
       ↓
execute_inventory_command()
       ↓
Shopify API Update
       ↓
Formatted Result
```

## Installation

The translator is included in the APEG package. Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Requirements

### Environment Variables

**Required**:
- `OPENAI_API_KEY`: Your OpenAI API key (for translation)
- `SHOPIFY_STORE_DOMAIN`: Your Shopify store domain
- `SHOPIFY_ACCESS_TOKEN`: Your Shopify API access token

**Optional**:
- `APEG_TEST_MODE`: Set to `true` to run in test mode without real API calls

### Example .env Setup

```bash
# OpenAI (required for translator)
OPENAI_API_KEY=sk-proj-...

# Shopify (required for execution)
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...

# Optional: Test mode
APEG_TEST_MODE=false
```

## Usage

### Option 1: Interactive CLI

Run the CLI in interactive mode:

```bash
python inventory_cli.py
```

This starts an interactive prompt where you can enter natural language requests:

```
====================================================================
  INVENTORY CLI - Natural Language Inventory Update Tool
====================================================================

Enter natural language inventory requests.
Examples:
  - "Update Tanzanite ankle bracelet: Medium to 3, Large to 5"
  - "Set Tanzanite anklets Cable/Medium to 2, Cable/Large to 1"

Type 'quit' or 'exit' to exit.
Type 'dry-run <text>' to see the translated command without executing.

--------------------------------------------------------------------

📦 Enter inventory request (or 'quit' to exit):
```

#### Example Session

```
📦 Enter inventory request: Update Tanzanite ankle bracelet: Medium to 3, Large to 5

Processing: Update Tanzanite ankle bracelet: Medium to 3, Large to 5
----------------------------------------------------------------------

[1] Translating natural language to InventoryCommand...

[2] Generated command:
{
  "task_type": "inventory_update",
  "store": "dev",
  "product_title": "Tanzanite ankle bracelet",
  "variants": [
    {
      "variant_label": "Medium",
      "new_quantity": 3
    },
    {
      "variant_label": "Large",
      "new_quantity": 5
    }
  ]
}

[3] Executing inventory command...

[4] Result:
Status: success
Store: dev
Product: TEST - Handmade Sterling Silver Beaded Ankle Bracelets  | Birthstone Tanzanite December
Product ID: 8896138903862

Variant Updates:
  - Medium (ID: 46853092245814)
    Status: success
    Quantity: 1 → 3
  - Large (ID: 46853092278582)
    Status: success
    Quantity: 2 → 5

====================================================================
```

### Option 2: Stdin Mode

Pipe input to the CLI for non-interactive use:

```bash
echo "Set Tanzanite anklets Medium to 10" | python inventory_cli.py
```

### Option 3: Dry-Run Mode

Test the translation without executing the command:

```
📦 Enter inventory request: dry-run Update Tanzanite Medium to 15

[DRY RUN] Processing: Update Tanzanite Medium to 15
----------------------------------------------------------------------

[1] Translating natural language to InventoryCommand...

[2] Generated command:
{
  "task_type": "inventory_update",
  "store": "dev",
  "product_title": "Tanzanite",
  "variants": [
    {
      "variant_label": "Medium",
      "new_quantity": 15
    }
  ]
}

[DRY RUN] Skipping execution.
```

### Option 4: Python API

Use the translator directly in your Python code:

```python
from apeg_core.translators.inventory_text_to_command import (
    build_inventory_command_from_text,
    format_inventory_result,
)
from apeg_core.services.shopify_inventory_service import (
    execute_inventory_command,
)

# Translate natural language to command
user_text = "Update Tanzanite ankle bracelet: Medium to 3, Large to 5"
command = build_inventory_command_from_text(user_text)

# Execute the command
result = execute_inventory_command(command)

# Format the result
summary = format_inventory_result(result)
print(summary)
```

## InventoryCommand Schema

**Schema Module**: `src/apeg_core/schemas/inventory_commands.py`

The canonical schema for inventory commands is defined in the `inventory_commands` module, which provides:
- **InventoryUpdateCommand**: Pydantic model for inventory updates
- **InventoryQueryCommand**: Pydantic model for inventory queries (planned)
- **parse_inventory_context()**: Helper to validate and parse commands
- **Example contexts**: Ready-to-use example payloads

The translator generates commands matching this schema:

```json
{
  "task_type": "inventory_update",
  "store": "dev",
  "product_title": "string (product title or substring)",
  "variants": [
    {
      "variant_label": "string (variant label or substring)",
      "new_quantity": integer (>= 0)
    }
  ]
}
```

### Type-Safe Validation

For type-safe validation in your code:

```python
from apeg_core.schemas.inventory_commands import (
    parse_inventory_context,
    InventoryUpdateCommand,
)

# Validate and parse a command dict
command_dict = {...}
try:
    cmd = parse_inventory_context(command_dict)
    if isinstance(cmd, InventoryUpdateCommand):
        # Now you have a fully validated, type-checked command
        result = execute_inventory_command(cmd.to_context_dict())
except InventoryContextParseError as e:
    print(f"Invalid command: {e}")
```

### Field Descriptions

- **task_type**: Must be `"inventory_update"` (only supported type currently)
- **store**: Target store identifier (currently only `"dev"` is supported)
- **product_title**: Product title or substring to match (case-insensitive)
- **variants**: List of variant updates (at least one required)
  - **variant_label**: Variant label or substring to match (e.g., "Medium", "Cable / Large")
  - **new_quantity**: Absolute quantity to set (not a delta)

## Natural Language Examples

The translator can understand various natural language formats:

### Basic Updates

```
"Set Tanzanite ankle bracelet Medium to 5"
"Update Tanzanite Medium to 10"
"Change Tanzanite Large to 3"
```

### Multiple Variants

```
"Update Tanzanite ankle bracelet: Medium to 3, Large to 5"
"Set Tanzanite anklets Cable/Medium to 2, Cable/Large to 1"
"Update Tanzanite: Medium = 10, Large = 15, Small = 5"
```

### Descriptive Requests

```
"I need to set the Tanzanite December ankle bracelet inventory to: Medium = 3, Large = 4"
"Please update the inventory for Tanzanite anklets: set Medium to 5 and Large to 8"
```

## Error Handling

The translator and CLI handle several error conditions:

### Missing API Key

```
❌ Error: OPENAI_API_KEY environment variable not set
Please set your OpenAI API key to use the translator.
```

### Invalid Translation

```
❌ Translation Error: Translator output was not valid JSON: ...
```

### Product Not Found

```
❌ Inventory Command Error: No product found matching title filter: 'NonexistentProduct'
```

### Variant Not Found

```
❌ Inventory Command Error: No variant found matching label 'XL' in product 'Tanzanite Ankle Bracelet'
```

## Testing

Run the test suite:

```bash
# Run all translator tests
pytest tests/test_inventory_translator.py -v

# Run with coverage
pytest tests/test_inventory_translator.py --cov=apeg_core.translators -v
```

### Test Coverage

The test suite includes:
- ✅ API key validation
- ✅ Successful translation scenarios
- ✅ Markdown code fence stripping
- ✅ Invalid JSON handling
- ✅ Invalid task_type handling
- ✅ Missing variants handling
- ✅ Result formatting (single and multiple variants)
- ✅ Empty updates handling

## Development

### Adding New Translation Features

To enhance the translator's capabilities:

1. **Update the System Prompt**: Modify `INVENTORY_COMMAND_SCHEMA_DOC` in `inventory_text_to_command.py`
2. **Add Validation**: Update `build_inventory_command_from_text()` to validate new fields
3. **Add Tests**: Create new test cases in `tests/test_inventory_translator.py`
4. **Update Documentation**: Add examples to this README

### Supported Models

Current model: `gpt-4o-mini`

To change the model, edit the `model` parameter in `build_inventory_command_from_text()`:

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Change this
    messages=messages,
    temperature=0.2,
)
```

## Integration with Existing Services

The translator is designed to work seamlessly with:

- **ShopifyAgent** (`apeg_core.agents.shopify_agent`)
- **Shopify Inventory Service** (`apeg_core.services.shopify_inventory_service`)
- **APEG Server** (`apeg_core.server`) - Can be integrated into `/run` endpoint

### Example Server Integration

```python
from fastapi import HTTPException
from apeg_core.translators.inventory_text_to_command import (
    build_inventory_command_from_text
)
from apeg_core.services.shopify_inventory_service import (
    execute_inventory_command
)

@app.post("/inventory/natural")
async def natural_language_inventory(request: dict):
    """Execute inventory update from natural language."""
    user_text = request.get("text")
    if not user_text:
        raise HTTPException(status_code=400, detail="Missing 'text' field")

    try:
        command = build_inventory_command_from_text(user_text)
        result = execute_inventory_command(command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Troubleshooting

### Issue: "Empty response from inventory translator model"

**Cause**: OpenAI API returned no content
**Solution**: Check API key validity and network connection

### Issue: "Translator output was not valid JSON"

**Cause**: Model returned malformed JSON or wrapped in markdown
**Solution**: The translator automatically strips markdown fences. If the issue persists, check the model temperature setting.

### Issue: "No product found matching title filter"

**Cause**: Product title doesn't match any products in Shopify
**Solution**: Use a more specific or different substring. Check exact product titles in Shopify admin.

### Issue: "No variant found matching label"

**Cause**: Variant label doesn't match any variants for the product
**Solution**: Check exact variant labels in Shopify. Common labels include "Medium", "Large", "Cable / Medium", etc.

## Performance

- **Translation Time**: ~1-3 seconds (depends on OpenAI API latency)
- **Execution Time**: ~1-2 seconds per variant (depends on Shopify API latency)
- **Cost**: ~$0.0001-0.0003 per translation (GPT-4o-mini pricing)

## Future Enhancements

Potential improvements:

- [ ] Support for bulk updates (multiple products)
- [ ] Support for relative quantity changes (e.g., "+5", "-3")
- [ ] Support for multiple stores
- [ ] Caching of recent translations
- [ ] Support for other inventory operations (e.g., stock checks)
- [ ] Integration with other e-commerce platforms (Etsy, WooCommerce)
- [ ] Webhook support for automated inventory updates

## License

MIT License - See LICENSE file for details

## Related Documentation

- [APEG Core Documentation](../README.md)
- [Inventory Command Schema](../src/apeg_core/schemas/inventory_commands.py) - Canonical schema definitions
- [Shopify Inventory Service](../src/apeg_core/services/shopify_inventory_service.py) - Command execution
- [Inventory Translator](../src/apeg_core/translators/inventory_text_to_command.py) - NL translation
- [Shopify Integration Guide](shopify_integration.md) (if exists)
- [API Reference](api_reference.md) (if exists)

---

**Last Updated**: 2025-11-27
**Version**: 1.0.0
**Maintainer**: PEG Development Team
