# FoundryVTT REST API - Search Endpoint Quick Reference

## Key Findings for Your Project

### 1. The 200-Result Limit Challenge

**Problem**: You can only get 200 results from a single `/search` request

**Location**: Hardcoded in Foundry module at `/src/ts/network/routers/search.ts` line 54
```typescript
const filteredResults = await window.QuickInsert.search(data.query, filterFunc, 200);
```

**Solution**: Use `/structure` or `/contents/:path` instead for bulk compendium access

---

## 2. Getting All Items from a Compendium (No Limit)

### Recommended: Use `/structure` endpoint

```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/structure?clientId=YOUR_CLIENT_ID&path=Compendium.dnd5e.items" \
  -H "x-api-key: YOUR_API_KEY"
```

Returns all items in the compendium without pagination limit.

### Alternative: Use `/contents/:path` endpoint

```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/contents/Compendium.dnd5e.items?clientId=YOUR_CLIENT_ID" \
  -H "x-api-key: YOUR_API_KEY"
```

Functionally equivalent to `/structure` for compendium access.

---

## 3. Search Filter Examples

### Simple Filters (Single Type)
```
filter=Actor           # Same as documentType:Actor
filter=Item            # Same as documentType:Item
```

### Property-Based Filters (Key:Value)
```
filter=documentType:Actor
filter=package:dnd5e.items
filter=subType:spell
filter=resultType:CompendiumSearchItem
filter=name:Fireball
```

### Multiple Filters (AND Logic)
```
filter=documentType:Actor,package:dnd5e.monsters
filter=subType:npc,documentType:Actor
filter=package:dnd5e.items,name:Sword
```

### Advanced Filters (Undocumented)
```
filter=resultType:CompendiumSearchItem        # Compendium items only
filter=resultType:EntitySearchItem            # World items only
filter=system.attributes.hp.max:10            # Nested properties
```

---

## 4. Search Result Types

QuickInsert returns results with different `resultType` values:

| Result Type | Meaning | From |
|-------------|---------|------|
| `CompendiumSearchItem` | Item from compendium | Module/system compendiums |
| `EntitySearchItem` | Item from world | Created in the world |
| `EmbeddedEntitySearchItem` | Item in an actor/item | Nested under another entity |

---

## 5. Search Response Format

```json
{
  "requestId": "search_1743293916350_z1qzxje",
  "clientId": "foundry-DKL4ZKK80lUZFgSJ",
  "query": "abo",
  "filter": "actor",
  "totalResults": 2,
  "results": [
    {
      "documentType": "Actor",
      "id": "shhHtE7b92PefCWB",
      "name": "Aboleth",
      "package": "dnd5e.monsters",
      "packageName": "Monsters (SRD)",
      "subType": "npc",
      "uuid": "Compendium.dnd5e.monsters.shhHtE7b92PefCWB",
      "icon": "<i class=\"fas fa-user entity-icon\"></i>",
      "journalLink": "@UUID[Compendium.dnd5e.monsters.shhHtE7b92PefCWB]{Aboleth}",
      "tagline": "Monsters (SRD)",
      "formattedMatch": "<strong>Abo</strong>leth",      // Highlighted match
      "resultType": "CompendiumSearchItem",               // Type of result
      "folder": null                                      // Folder if applicable
    }
  ]
}
```

### Important Fields
- `formattedMatch`: HTML with `<strong>` tags showing matched text
- `resultType`: Constructor name (CompendiumSearchItem, EntitySearchItem, etc.)
- `folder`: Folder ID if the item is in a folder
- `uuid`: Full UUID for fetching full entity data

---

## 6. Getting Full Entity Data

Search returns partial data. For full details:

```bash
# Get full item data
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/get?clientId=YOUR_CLIENT_ID&uuid=Compendium.dnd5e.monsters.shhHtE7b92PefCWB" \
  -H "x-api-key: YOUR_API_KEY"
```

Use the UUID from search results to fetch complete entity data.

---

## 7. How The Search Works

### Request Flow
1. HTTP request to `/search` endpoint
2. Relay validates parameters and generates unique `requestId`
3. Relay sends WebSocket message to Foundry client
4. Foundry module receives message, parses filter
5. Calls `QuickInsert.search(query, filterFunc, 200)` with 200-result limit
6. Foundry module maps results and sends back via WebSocket
7. Relay receives response and returns HTTP response

### Key Points
- **Relay doesn't filter**: The relay just forwards WebSocket messages
- **Foundry does filtering**: The Foundry module applies filters after QuickInsert search
- **200-limit is in Foundry**: NOT in the relay server
- **Filter logic is AND**: All filters must match (not OR)
- **Case-sensitive filters**: Simple filters like `filter=Actor` are case-sensitive

---

## 8. When to Use Each Endpoint

### Use `/search` when:
- You want to find items by name/keyword
- You want filtered results (by type, package, etc.)
- You expect <200 results
- You want formatted match highlighting

### Use `/structure` when:
- You need ALL items from a compendium (no 200 limit)
- You want to list folders and their contents
- You want to explore world organization
- You need index entries with basic metadata

### Use `/contents/:path` when:
- You need direct access to a specific folder or compendium
- You want a flat list of all items in one container
- You prefer simpler endpoint than `/structure`

### Use `/get` when:
- You have a UUID and need complete entity data
- You need all properties of an entity
- You're following up on a search result

---

## 9. Practical Code Examples for Your Project

### Find all monsters from a compendium
```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/search?clientId=c1&query=&filter=documentType:Actor,package:dnd5e.monsters" \
  -H "x-api-key: YOUR_API_KEY"
# Limited to 200 results
```

### Get all items from compendium (no limit)
```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/structure?clientId=c1&path=Compendium.dnd5e.items" \
  -H "x-api-key: YOUR_API_KEY"
# Returns all items in the compendium
```

### Search for spells by name
```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/search?clientId=c1&query=fireball&filter=subType:spell" \
  -H "x-api-key: YOUR_API_KEY"
```

### Find items only in world (not compendiums)
```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/search?clientId=c1&query=&filter=resultType:EntitySearchItem" \
  -H "x-api-key: YOUR_API_KEY"
```

---

## 10. Important Limitations

1. **QuickInsert Dependency**: Search fails if QuickInsert module isn't installed
2. **200-Result Hard Limit**: Search has hardcoded 200-result limit
3. **No Pagination**: QuickInsert search doesn't support offset/limit parameters
4. **10-Second Timeout**: Relay times out search requests after 10 seconds
5. **Index Initialization**: Slow first search (adds 500ms for index creation)
6. **Partial Data**: Search results don't include full entity data

---

## 11. Modifying the 200-Limit

If you need more than 200 results from search, you need to modify the Foundry module:

**File**: `foundryvtt-rest-api/src/ts/network/routers/search.ts`
**Line**: 54

Change:
```typescript
const filteredResults = await window.QuickInsert.search(data.query, filterFunc, 200);
```

To:
```typescript
const filteredResults = await window.QuickInsert.search(data.query, filterFunc, 500); // or higher
```

**Warning**: Increasing this limit may cause performance issues on large Foundry installations.

---

## 12. Troubleshooting

### "QuickInsert not available"
- Make sure QuickInsert module is installed and enabled in Foundry
- Check module settings and console for errors

### Search returns fewer results than expected
- Check if you hit the 200-result limit
- Try using `/structure` endpoint instead for bulk operations

### Filter not working
- Ensure proper syntax: `filter=key:value`
- Multiple filters: `filter=key1:value1,key2:value2`
- Remember AND logic: all filters must match

### Timeout errors
- Search taking too long
- May be due to QuickInsert index initialization (first search is slower)
- Large Foundry installations take longer to search

---

## 13. Related Files in Repository

- `/src/foundry/journals.py` - Your journal upload code
- `/src/foundry/client.py` - FoundryClient wrapper
- Check `FOUNDRY_RELAY_URL` environment variable in `.env`

---

## Quick Checklist

- [ ] 200-result limit is in Foundry module, not relay
- [ ] Use `/structure` for bulk compendium access (no limit)
- [ ] Filter parameter is optional but very useful
- [ ] Filter syntax: `key:value` or `key1:value1,key2:value2`
- [ ] All filters use AND logic (must all match)
- [ ] Search results include `uuid` for fetching full data
- [ ] Set `x-api-key` header for all requests
- [ ] Include `clientId` parameter for all requests
- [ ] 10-second timeout on relay for search requests

