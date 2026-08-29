# Capture Protocol (Route 2 — Stock Apps)

**Device:** any iPhone 15 or newer for Photo/Video tiers; a Pro-class iPhone (LiDAR sensor) for the LiDAR tier. Tested on iPhone 16 Pro.

## 1. Install (one-time, before visiting the property)
1. **Camera** — already on the phone. No setup.
2. **3D Scanner App** by AI Photo Editor Lab SRL. Free tier is sufficient. Open it once and grant Camera access when prompted.

## 2. Per-room capture order
Capture **one room at a time, fully, before moving to the next.** For each room, in this order:

### A. Photos (2–8 stills)
- Open **Camera**, photo mode.
- Stand near the center of the room. Take one photo facing each wall (4 photos for a rectangular room), plus one of the ceiling/floor if damage or an unusual feature is there.
- Keep the whole wall — floor to ceiling — in frame. Don't zoom.
- Avoid: backlighting a window (blows out exposure), your own reflection in mirrors/glass (step to the side), extreme close-ups.

### B. Video (one walkthrough clip)
- Open **Camera**, video mode.
- Start recording just inside the doorway. Walk the room's perimeter once, slowly (roughly 10 seconds per wall), holding the phone at chest height, pointed slightly down-and-forward. Turn your body, don't just pan the phone.
- Pause 2 seconds facing each corner and each opening (door/window) before continuing.
- One continuous take, ~30–90 seconds total. Stop recording before leaving the room.
- Avoid: fast whipping turns, walking backwards, stepping outside the room mid-clip.

### C. LiDAR (3D Scanner App)
- Open **3D Scanner App** → New Scan → Scan Mode ("LiDAR") → Tap **Recording Buttton** to start LiDAR recording.
- Start in a corner. Walk the full perimeter slowly (one small step every 1–2 seconds), keeping every wall, the ceiling, and the floor in view at some point during the pass. Do a second slower pass over any damaged surface, holding the phone ~0.5m from it.
- Keep the app's on-screen mesh overlay filling in with no big gaps before stopping.
- Avoid: moving faster than the mesh can keep up (app might flash a warning), scanning through un-lit rooms (turn lights on), skipping mirrored/glass walls (scan them anyway — depth will be noisy there and that's expected, not user error).
- Tap **Record Stop Button (middle)**, then Process scan (HD), then tap on **Start**, **Share → All Data**. Do **not** use "Point Cloud" export — it's pre-fused and drops per-frame poses our pipeline needs.

## 3. Repeatability room (benchmark only)
For the one room designated for the repeatability gate, repeat steps A–C a second time, without changing anything in the room, before moving on. Name it `<room>_take2` at handoff (see below).

## 4. Handoff to the pipeline
1. AirDrop the room's photos, video, and the "All Data" LiDAR export **all together, in one batch**, to the capture Mac. AirDrop's save location is set to this repo's `media/inbox/` folder.
2. On the Mac, run `python scripts/sort_media.py --watch` (start it before AirDropping, or run it after — it processes whatever's waiting).
3. When prompted `Room name for this burst:`, type the room's name (lowercase, hyphenated, e.g. `living-room`, or `living-room_take2` for a repeat).
4. Confirm the prompt returns to watching, then repeat steps 1–3 for the next room.

## What "ambiguous" looks like (avoid these)
- Skipping a wall in the video walkthrough.
- Taking all photos from one spot without turning.
- Ending the LiDAR scan with visible holes in the mesh overlay.
- Sending files from two different rooms in the same AirDrop batch.
