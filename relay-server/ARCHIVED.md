# Relay Server - ARCHIVED

**This component is deprecated and no longer used.**

The relay server was previously used to bridge HTTP requests to FoundryVTT via WebSocket. It has been replaced by:

1. **Direct WebSocket endpoint** in the FastAPI backend (`/ws/foundry`)
2. **Tablewrite Foundry module** that connects directly to the backend

## Why Archived

- **Simplified architecture**: One less component to deploy and maintain
- **No external relay dependency**: Direct connection between backend and Foundry
- **Better reliability**: Fewer network hops, simpler debugging
- **Easier deployment**: Single container instead of two services
- **Reduced latency**: Push notifications delivered immediately to Foundry

## What the Relay Server Did

The relay server (based on ThreeHats REST API) provided:
- HTTP to WebSocket bridge for FoundryVTT communication
- REST API endpoints that translated to Foundry document operations
- Authentication and client management

This functionality is now handled directly by the FastAPI backend's WebSocket endpoint.

## Migration Steps

If you were using the relay server:

1. **Remove relay server configuration from `.env`**:
   ```bash
   # Remove or comment out these lines:
   # FOUNDRY_RELAY_URL=http://localhost:3010
   ```

2. **Stop the relay server** (if running):
   ```bash
   cd relay-server && docker-compose -f docker-compose.local.yml down
   ```

3. **Install the Tablewrite Foundry module**:
   ```bash
   # Copy module to Foundry's modules directory
   cp -r foundry-module/tablewrite-assistant/ /path/to/foundry/Data/modules/tablewrite-assistant/
   ```

4. **Enable and configure the module in Foundry**:
   - Go to Game Settings -> Manage Modules
   - Enable "Tablewrite Assistant"
   - Configure backend URL in module settings (default: `http://localhost:8000`)

5. **Start the new backend**:
   ```bash
   # Option A: Docker
   docker-compose -f docker-compose.tablewrite.yml up -d

   # Option B: Direct
   cd ui/backend && uvicorn app.main:app --reload --port 8000
   ```

## Keeping the Code

The relay server code is preserved in this directory for reference but is not actively maintained. If you need the relay server functionality for legacy reasons, it should still work, but no new features or bug fixes will be added.

## New Architecture

```
Before (with relay server):
Backend -> HTTP -> Relay Server -> WebSocket -> Foundry Module -> FoundryVTT

After (direct WebSocket):
Backend -> WebSocket -> Tablewrite Module -> FoundryVTT
```

The new architecture pushes content directly to connected Foundry clients when actors, journals, or scenes are created through the Web UI.
