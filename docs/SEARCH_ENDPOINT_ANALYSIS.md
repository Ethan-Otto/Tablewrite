# FoundryVTT REST API - Search Endpoint Analysis

## Executive Summary

The search endpoint in the FoundryVTT REST API relay is a WebSocket-based request/response system that leverages FoundryVTT's QuickInsert module for full-text searching across compendiums and world entities. The 200-result limit is hardcoded in the Foundry module side, not the relay.

---

## 1. Search Endpoint Overview

### Request Flow Architecture

```
HTTP Request (REST API) 
    ↓
Relay Server (search.ts route handler)
    ↓
WebSocket Message to Foundry Client
    ↓
Foundry Module (search router)
    ↓
QuickInsert.search() method
    ↓
Filter results locally
    ↓
Send back via WebSocket
    ↓
HTTP Response
```

### Endpoint Details

**URL**: `/search`
**Method**: `GET`
**Required Parameters**:
- `clientId` (query): Auth token for specific Foundry world
- `query` (query): Search string

**Optional Parameters**:
- `filter` (query): Filter string (simple or property-based)

**Headers**:
- `x-api-key`: API key for authentication

---

## 2. Implementation Deep Dive

### Relay Side: `/tmp/foundryvtt-rest-api-relay/src/routes/api/search.ts`

```typescript
searchRouter.get("/search", ...commonMiddleware, createApiRoute({
    type: 'search',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' },
        { name: 'query', from: 'query', type: 'string' }
    ],
    optionalParams: [
        { name: 'filter', from: 'query', type: 'string' }
    ]
}));
```

**What happens**:
1. Request parameters extracted from query string
2. Client lookup via `ClientManager.getClient(clientId)`
3. WebSocket message sent to Foundry client with type `'search'`
4. Relay waits for `'search-result'` message from Foundry
5. Response returned to HTTP client

**Flow in `createApiRoute` (route-helpers.ts)**:
- Validates parameters
- Generates unique `requestId` (format: `search_${timestamp}`)
- Stores pending request in Map with 10-second default timeout
- Sends WebSocket message to Foundry client
- Message handler receives response and sends HTTP response

---

### Foundry Side: `/tmp/foundryvtt-rest-api/src/ts/network/routers/search.ts`

```typescript
router.addRoute({
  actionType: "search",
  handler: async (data, context) => {
    // Check if QuickInsert module is available
    if (!window.QuickInsert) {
      // Error response
      return;
    }

    // Ensure index is ready
    if (!window.QuickInsert.hasIndex) {
      window.QuickInsert.forceIndex();
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Parse filters if provided
    let filterFunc = null;
    if (data.filter) {
      const filters = typeof data.filter === 'string' ? 
        parseFilterString(data.filter) : data.filter;

      filterFunc = (result: any) => {
        return matchesAllFilters(result, filters);
      };
    }

    // SEARCH WITH 200-RESULT LIMIT
    const filteredResults = await window.QuickInsert.search(data.query, filterFunc, 200);

    // Map results to response format
    socketManager?.send({
      type: "search-result",
      requestId: data.requestId,
      query: data.query,
      filter: data.filter,
      results: filteredResults.map(result => ({
        documentType: result.item.documentType,
        folder: result.item.folder,
        id: result.item.id,
        name: result.item.name,
        package: result.item.package,
        packageName: result.item.packageName,
        subType: result.item.subType,
        uuid: result.item.uuid,
        icon: result.item.icon,
        journalLink: result.item.journalLink,
        tagline: result.item.tagline || "",
        formattedMatch: result.formattedMatch || "",
        resultType: result.item.constructor?.name
      }))
    });
  }
});
```

**Key Points**:
- **200-Result Hardcoded Limit**: Line 54 in search.ts passes `200` as the result limit to `QuickInsert.search()`
- **Filter Processing**: Occurs BEFORE search, filtering function passed to QuickInsert
- **Index Dependency**: Requires QuickInsert module with valid index
- **Result Mapping**: Only certain properties are returned in the response

---

## 3. Filter System Analysis

### Filter Parsing (`/tmp/foundryvtt-rest-api/src/ts/utils/search.ts`)

```typescript
export function parseFilterString(filterStr: string): Record<string, string> {
    if (!filterStr.includes(':')) {
      return { documentType: filterStr };  // Simple filter: "Actor"
    }
    
    const filters: Record<string, string> = {};
    const parts = filterStr.split(',');
    
    for (const part of parts) {
      if (part.includes(':')) {
        const [key, value] = part.split(':');
        filters[key.trim()] = value.trim();
      }
    }
    
    return filters;
}
```

### Supported Filter Properties

**Simple Format**:
- `filter=Actor` → filters by `documentType: "Actor"`
- `filter=Item` → filters by `documentType: "Item"`

**Property-Based Format (colon-separated)**:
- `filter=documentType:Actor`
- `filter=package:dnd5e.items`
- `filter=name:Fireball`
- `filter=subType:spell`
- `filter=resultType:CompendiumSearchItem`

**Multiple Filters (comma-separated)**:
- `filter=documentType:Actor,package:dnd5e.monsters`
- `filter=subType:npc,documentType:Actor`

### Filter Matching Logic (`matchesAllFilters` function)

The matching function has special handling for several properties:

**1. `resultType`**: Constructor name matching (CompendiumSearchItem, EntitySearchItem, etc.)
```typescript
if (key === "resultType") {
  const itemConstructorName = result.item?.constructor?.name;
  if (!itemConstructorName || 
      itemConstructorName.toLowerCase() !== value.toLowerCase()) {
    return false;
  }
}
```

**2. `package`**: Compendium package matching with flexible formats
```typescript
if (key === "package" && result.item) {
  const packageValue = result.item.package;
  
  // Accepts: "dnd5e.items", "Compendium.dnd5e.items"
  if (packageValue.toLowerCase() !== value.toLowerCase() && 
      !(`Compendium.${packageValue}`.toLowerCase() === value.toLowerCase())) {
    return false;
  }
}
```

**3. `folder`**: Folder ID matching with multiple format support
```typescript
if (key === "folder" && result.item) {
  const folderValue = result.item.folder;
  
  if (!folderValue && value) return false;
  
  if (folderValue) {
    const folderIdMatch = typeof folderValue === 'object' ? folderValue.id : folderValue;
    
    // Accepts: "zmAZJmay9AxvRNqh", "Folder.zmAZJmay9AxvRNqh"
    if (value === folderIdMatch || 
        value === `Folder.${folderIdMatch}` ||
        `Folder.${value}` === folderIdMatch) {
      continue;
    }
    return false;
  }
}
```

**4. Standard Properties**: Case-insensitive string matching
- `name`, `subType`, `documentType`, `id`, `uuid`, etc.
- Also supports nested property access: `system.attributes.hp`

---

## 4. The 200-Result Limit

### Where is it enforced?

**Location**: `/tmp/foundryvtt-rest-api/src/ts/network/routers/search.ts`, line 54

```typescript
const filteredResults = await window.QuickInsert.search(data.query, filterFunc, 200);
```

**Who enforces it**: The Foundry REST API module (NOT the relay server)

### Why 200?

- This is a hardcoded limit to prevent performance issues
- QuickInsert is a full-text search index and can return large result sets
- The 200 limit is reasonable for most use cases
- The relay server doesn't know about this limit—it simply receives whatever Foundry returns

---

## 5. Other Bulk/Compendium Endpoints

### Alternative Approaches for Getting All Items

#### 1. `/structure` Endpoint (Bulk catalog retrieval)

**Purpose**: Get folder/compendium structure with optional entity data

**URL**: `GET /structure?clientId={id}`

**Key Parameters**:
- `clientId` (required)
- `includeEntityData` (optional): Include full entity data
- `path` (optional): Specific compendium or folder path (e.g., `Compendium.dnd5e.items`)
- `recursive` (optional): Recurse into nested folders
- `recursiveDepth` (optional): How deep to recurse (default: 5)
- `type` (optional): Filter by entity type (Scene, Actor, Item, etc.)

**Implementation**: `/tmp/foundryvtt-rest-api/src/ts/network/routers/structure.ts`

**Key Feature**: 
- Can fetch all items in a compendium if you know the compendium ID
- Returns index entries for compendiums (NOT full detailed data)
- No pagination limit on structure endpoint itself

**Example Response** (for compendium):
```json
{
  "compendium": {
    "name": "Items (SRD)",
    "type": "Item",
    "entities": [
      {
        "uuid": "dnd5e.items.00BggOkChWztQx6R",
        "name": "Studded Leather Armor +3",
        "id": "00BggOkChWztQx6R",
        "type": "Item"
      },
      // ... more items
    ]
  }
}
```

#### 2. `/contents/:path` Endpoint (Direct compendium access)

**Purpose**: Get contents of a specific folder or compendium

**URL**: `GET /contents/Compendium.dnd5e.items?clientId={id}`

**Implementation**: `/tmp/foundryvtt-rest-api/src/ts/network/routers/structure.ts` (contents route)

**Returns**: All entries in the specified compendium/folder

**Difference from /structure**:
- Direct access to single path
- Returns entries without hierarchy/folder structure
- No pagination limit documented

---

## 6. How to Retrieve All Items from a Compendium

### Option 1: Use `/structure` endpoint (Recommended for bulk)

```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/structure?clientId=YOUR_CLIENT_ID&path=Compendium.dnd5e.items" \
  -H "x-api-key: YOUR_API_KEY"
```

**Pros**:
- No 200-result limit
- Returns all items in compendium
- Returns item metadata (UUID, name, ID, type)

**Cons**:
- Returns minimal data (just index entries)
- Need full item details separately via `/get` endpoint

### Option 2: Use `/contents/:path` endpoint

```bash
curl -X GET \
  "https://foundryvtt-rest-api-relay.fly.dev/contents/Compendium.dnd5e.items?clientId=YOUR_CLIENT_ID" \
  -H "x-api-key: YOUR_API_KEY"
```

**Very similar to /structure**—effectively the same information returned

### Option 3: Paginate `/search` endpoint

**Conceptually possible but not implemented**:
- Could theoretically search with different offsets
- QuickInsert search doesn't support offset/pagination parameters
- Not recommended due to 200-result hard limit

---

## 7. Comparison Table

| Endpoint | Limit | Pagination | Returns Full Data | Best For |
|----------|-------|-----------|-------------------|----------|
| `/search` | 200 results | None (hardcoded) | Partial (formatted) | Quick lookups, filtering |
| `/structure` | None documented | Via path hierarchy | Index entries only | Bulk listing, compendium inventory |
| `/contents/:path` | None documented | Via path | Index entries only | Direct compendium access |
| `/get` | 1 entity | N/A | Full entity data | Getting individual item details |

---

## 8. Undocumented Features & Findings

### Hidden Capabilities

#### 1. Search Filter Chaining
Multiple filters can be applied simultaneously:
```
filter=documentType:Actor,package:dnd5e.monsters,subType:npc
```
All filters must match (AND logic, not OR).

#### 2. Nested Property Filtering
The filter system supports dot-notation for nested properties:
```
filter=system.attributes.hp.max:10
```
This is implemented in the `matchesAllFilters` function but not documented.

#### 3. Constructor-Name Filtering
```
filter=resultType:CompendiumSearchItem
```
Different result types from QuickInsert:
- `CompendiumSearchItem`: Items from compendiums
- `EntitySearchItem`: Items from world
- `EmbeddedEntitySearchItem`: Embedded items (actors' items, etc.)

#### 4. Response Properties Not in Documentation

The search response includes `formattedMatch`:
```json
"formattedMatch": "<strong>Abo</strong>leth"
```
This is HTML-formatted match highlighting showing which part of the name matched the query.

Also includes `resultType` (constructor name) and `folder` (folder reference if available).

### Limitations Not Documented

1. **QuickInsert Dependency**: Search FAILS if QuickInsert module isn't installed or enabled
2. **Index Initialization**: Search forces index creation if not ready, adding 500ms delay
3. **Response Size**: While there's no documented limit on relay, 200 items per search is limit
4. **Timeout**: Relay has 10-second default timeout for search responses
5. **Filter Case Sensitivity**: Simple filters (like `filter=Actor`) are case-sensitive in the documentType comparison

---

## 9. Filtering Detailed Examples

### Finding Monsters
```
GET /search?clientId=c1&query=dragon&filter=documentType:Actor,package:dnd5e.monsters
```
Returns all monsters with "dragon" in name or details.

### Finding Spells by Subtype
```
GET /search?clientId=c1&query=fireball&filter=subType:spell
```

### Finding World-Only Items (not compendium)
```
GET /search?clientId=c1&query=sword&filter=resultType:EntitySearchItem
```

### Folder-Based Search
```
GET /search?clientId=c1&query=&filter=folder:abc123xyz
```
Returns all items in a specific folder.

---

## 10. Architecture & Data Flow Summary

```
Client HTTP Request
    ↓
Relay validates parameters (route-helpers.ts)
    ↓
Relay looks up WebSocket client (ClientManager)
    ↓
Relay sends WebSocket message:
    {
      type: "search",
      requestId: "search_1234567890",
      query: "...",
      filter: "..."
    }
    ↓
Foundry module receives message (search.ts router)
    ↓
Parse filter string → create filter function
    ↓
Call QuickInsert.search(query, filterFunc, 200)
    ↓
Map results to response format
    ↓
Send WebSocket message back:
    {
      type: "search-result",
      requestId: "search_1234567890",
      query: "...",
      results: [...]
    }
    ↓
Relay receives response, sends HTTP 200 response
    ↓
Client receives JSON response with search results
```

---

## 11. Key Code Files

**Relay Server**:
- `/src/routes/api/search.ts` - Search endpoint handler
- `/src/routes/route-helpers.ts` - createApiRoute function
- `/src/routes/shared.ts` - Request tracking and response handling
- `/src/core/ClientManager.ts` - WebSocket client management

**Foundry Module**:
- `/src/ts/network/routers/search.ts` - Search implementation in Foundry
- `/src/ts/utils/search.ts` - Filter parsing and matching logic
- `/src/ts/network/webSocketManager.ts` - WebSocket message handling

---

## 12. Summary: Key Findings

1. **200-Result Limit is in Foundry Module**: Not the relay—change in `/src/ts/network/routers/search.ts` line 54
2. **Type Parameter Does Filtering**: The `filter` parameter can use `documentType`, `resultType`, `package`, `folder`, or any property
3. **Filters are AND Logic**: Multiple filters all must match (not OR)
4. **Server-Side Filtering**: All filtering happens in Foundry after QuickInsert search, not in relay
5. **Relay is Just a Messenger**: Relay doesn't parse or filter—it forwards WebSocket messages bidirectionally
6. **Alternative for Bulk Operations**: Use `/structure` or `/contents/:path` endpoints for getting all items without pagination
7. **Undocumented Filter Flexibility**: Nested property filtering and constructor-name filtering available but not documented
8. **Formatted Matches Included**: Response includes HTML-formatted match highlighting via `formattedMatch` field
