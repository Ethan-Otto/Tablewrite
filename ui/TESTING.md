# Manual Testing Results

**Date:** 2025-11-03

## Test Cases

### Text Chat
- [ ] Regular text messages work
- [ ] Conversation history maintained

### Image Generation
- [ ] Explicit command: `/generate-image dragon`
- [ ] Natural language: "show me a castle"
- [ ] Custom count: "generate 3 images of a forest"
- [ ] Count capped at 4 (tested with "create 10 images")

### UI Components
- [ ] ImageCarousel displays correctly
- [ ] Navigation arrows work (prev/next)
- [ ] Image counter updates
- [ ] Single image: no arrows/counter
- [ ] Multiple images: arrows + counter visible
- [ ] Parchment aesthetic matches existing UI

### Error Handling
- [ ] Invalid requests show error message
- [ ] Error card styling matches design

## Known Issues

To be tested

## Testing Instructions

### Starting the Development Servers

**Backend:**
```bash
cd ui/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd ui/frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

### Test Scenarios

1. **Basic Text Chat**
   - Type: "Hello"
   - Expected: Gemini text response

2. **Image Generation - Explicit Command**
   - Type: "/generate-image a dragon"
   - Expected: Carousel with 2 dragon images

3. **Image Generation - Natural Language**
   - Type: "show me a castle"
   - Expected: Carousel with castle images

4. **Image Generation - Custom Count**
   - Type: "create 3 images of a forest"
   - Expected: Carousel with 3 forest images

5. **Image Generation - Max Limit**
   - Type: "generate 10 images of mountains"
   - Expected: Carousel with 4 images (capped at MAX_IMAGES_PER_REQUEST)

6. **Carousel Navigation**
   - Generate multiple images
   - Click left/right arrows
   - Expected: Images cycle through, counter updates

7. **Single Image UI**
   - Generate 1 image
   - Expected: No arrows or counter displayed

8. **Error Handling**
   - Test with invalid input or when backend is down
   - Expected: ErrorCard component displays with appropriate message

### Verification Checklist

- [ ] Backend server starts without errors
- [ ] Frontend dev server starts without errors
- [ ] No console errors in browser DevTools
- [ ] No TypeScript compilation errors
- [ ] All API requests return 200 status
- [ ] Images load correctly (no 404s)
- [ ] Carousel navigation is smooth
- [ ] Visual aesthetic matches design (wax seal buttons, parchment borders)
- [ ] Responsive layout works on different screen sizes
