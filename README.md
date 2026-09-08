# Drishti — Intelligent Border Video Analytics Platform

**SIH 2026 · PS 26187 · Ministry of Home Affairs / Sashastra Seema Bal**

Turns existing IP CCTV into an intelligent surveillance network. No FRS box,
no ANPR box, no smart cameras — the intelligence is entirely in software.

---

## Authentication

Drishti ships with a login screen and two auth backends. Copy `.env.example`
to `.env` and configure at least one.

### Supabase Auth (primary)

```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-publishable-anon-key
```

Create operator accounts in your Supabase dashboard under Authentication ->
Users. The browser holds the session; every API call and the WebSocket carry
the access token, and this backend **verifies the signature itself** rather
than trusting the client.

Verification prefers asymmetric signing keys (ES256/RS256) fetched from
`/auth/v1/.well-known/jwks.json`, which is Supabase's current recommendation.
A shared HS256 secret in the wrong hands can mint a token for any user. Legacy
HS256 projects still work via `SUPABASE_JWT_SECRET`.

### Local operator (offline fallback)

```bash
DRISHTI_OPERATOR=operator
DRISHTI_PASSWORD=<choose a strong password>
```

A border post can lose its uplink for days. An auth system that fails closed
when the link drops is useless there, so a locally-verified account is always
available. There is no default password: if `DRISHTI_PASSWORD` is unset, local
login is simply disabled.

If both are configured the login page shows a toggle. Local sessions live in
memory, so restarting the server signs everyone out.

For a bench demo only, `AUTH_REQUIRED=false` bypasses the login screen
entirely. Never do that in the field.

> **A note on air-gapped deployment.** Supabase Auth needs connectivity, which
> a remote BOP may not have. The local operator account exists for exactly
> that case, and every other part of the platform (models, inference, ledger)
> already runs fully offline. Only the web fonts and icon CSS load from a CDN;
> they degrade to system fonts without network.

---

## The two views

**Camera wall** shows every connected camera on one page. Each tile carries live
detection boxes and its own state:

| Tile state | Meaning |
|---|---|
| Grey border, `LIVE` | Nominal |
| **Amber** border, `ALERT` | A boundary was crossed on this camera |
| **Red** border, pulsing, `EMERGENCY` | Risk threshold breached, or the feed itself was tampered with |
| `NO SIGNAL` | Camera unreachable |

A banner across the top names the camera that needs attention and why
("EMERGENCY - BOP-02 Sector: Person crossed a boundary, pacing back and forth,
loitering 27s"). **Open camera** jumps straight to it. Alert state holds for 25
seconds after the last trigger so a glance at the wall still shows what just
happened.

**Operations** is the single-camera view: 3D tactical twin, boundary drawing,
per-track risk meters, forensic search, and the evidence chain.

---

## Quick start

**macOS / Linux**
```bash
./run.sh
```

**Windows**
```bash
run.bat
```

Then open **http://127.0.0.1:8000** and sign in.

First launch creates a virtualenv and installs dependencies (3–6 minutes).
Model weights are bundled in `models/`, so no download is needed after that
and the platform runs **fully offline** — which is the point, for a border post.

### In VS Code
Open this folder, then either press the Run button on `run.sh`, or use the
integrated terminal. To debug, select the `.venv` interpreter
(Cmd/Ctrl+Shift+P → *Python: Select Interpreter* → `./.venv`) and run
`backend/main.py` through uvicorn.

---

## Feeding data in

Three ways, all from the left panel of the dashboard:

| Source | How |
|---|---|
| **Live RTSP camera** | Paste the URL → *Connect RTSP* |
| **Local webcam** | *Webcam* button (fastest way to test) |
| **Recorded footage** | Drop any video file — it loops as a synthetic RTSP source |

RTSP URL formats:
```
Hikvision   rtsp://user:pass@192.168.1.64:554/Streaming/Channels/102
Dahua/CP+   rtsp://user:pass@192.168.1.108:554/cam/realmonitor?channel=1&subtype=1
ONVIF       rtsp://user:pass@192.168.1.64:554/onvif1
```

> **Use the sub-stream** (`/102` on Hikvision, `subtype=1` on Dahua). It is
> ~640×480, YOLO downscales to 640px anyway, and it cuts decode cost ~8×.
> This is what lets one node handle ten cameras instead of two.

No camera to hand? Generate a test clip:
```bash
python make_demo_video.py
```

---

## What it detects

| Category | Classes | Colour |
|---|---|---|
| **Human** | person | cyan |
| **Vehicle** | car, truck, bus, motorcycle, bicycle, train, boat | amber |
| **Animal** | dog, cow, horse, sheep, bird, cat, and more | green — **suppressed** |
| **Bag** | backpack, handbag, suitcase | pink |
| **Weapon** | knife, scissors (+ your custom model) | red |
| **Face** | YuNet CNN, searched inside person boxes | violet |

Animals actively *decay* toward zero risk. A stray dog on the fence line is the
single largest source of false alarms in real border CCTV, and it is treated as
a suppression signal, not a detection.

### About firearms — read this before you pitch it

**No pretrained model detects guns.** COCO — what every YOLO ships with — has
no firearm class. Any team claiming out-of-the-box gun detection is either
mistaken or using a model they fine-tuned themselves.

The honest options:
1. Fine-tune YOLO on a firearms dataset, export `weapons.pt`, drop it in
   `models/`. The app detects it at startup and runs it as a second pass.
2. Ship `knife`/`scissors`, which COCO genuinely has, and say so.

Option 1 is roughly one day with a public firearms dataset. Do it before the
finals — but never claim it until the weights exist.

---

## Boundaries

Select a camera → choose a boundary type → **Draw boundary** → click points,
double-click to close. Stored in normalised coordinates, so a boundary drawn on
a 640×480 preview still applies to the 1080p main stream.

| Kind | Behaviour |
|---|---|
| **Virtual fence** | Alarms on the transition into the polygon |
| **Restricted area** | Alarms on any presence inside |
| **Ignore region** | Suppresses everything inside — a road, a village, a swaying tree |

The ignore region matters more than it sounds. Most real-world false alarms
come from one predictable part of the frame.

---

## The risk engine

Detection tells you *what*. The risk engine tells you *whether it matters*.
Each track accumulates 0–100 from behaviour over time:

| Signal | Weight |
|---|---|
| Boundary crossed | +45 |
| Inside a monitored zone | +18 |
| Loitering past 12s | up to +25 |
| Pacing (≥3 direction reversals) | +22 |
| Running | +15 |
| Weapon nearby | +40 |
| Object abandoned >8s | +65 |
| At night | ×1.25 |
| **Animal** | **decays −6/frame** |

Scores rise fast and fall slowly, so a flicker cannot trip an alarm. Alerts fire
at 70. **A farmer walking parallel to the fence never alarms; someone pacing at
it for 20 seconds does.** That distinction is the whole project.

---

## Feed integrity — the cybersecurity layer

The oldest attack on monitored CCTV is not hacking the AI, it is **replacing the
feed**: splice a loop of empty road in, and guards watch nothing happen while a
crossing occurs. A normal NVR shows a green "connected" light the entire time.

Every frame is checked for:

| Attack | Detection |
|---|---|
| **Frozen feed** | Identical hash *and* byte-identical pixels. A live camera on a motionless scene still has sensor noise; a spliced feed does not. |
| **Replayed loop** | Current frames matching earlier ones at a fixed period |
| **Blinded lens** | Luminance and variance collapse together |

This is the demo moment judges remember: unplug the camera mid-pitch, inject a
looped clip, and the dashboard flags **FEED INTEGRITY COMPROMISED** while any
commercial NVR would show all-clear.

---

## Evidence chain

Footage used against an infiltrator has to survive a courtroom. Every event is
SHA-256 chained to its predecessor:

```
hash = SHA256(timestamp ‖ camera ‖ event ‖ risk ‖ frame_hash ‖ prev_hash)
```

Alter or delete any historical record and every subsequent hash breaks.
Click **Verify integrity** to walk the chain; it names the exact record that was
tampered with. Prove it live:

```bash
sqlite3 data/drishti.db "UPDATE events SET summary='nothing happened' WHERE idx=3"
```

Then hit Verify. It reports `✗ CHAIN BROKEN at #3`.

An officer cannot quietly delete an event to cover a lapse, and a defence
lawyer cannot claim the footage was doctored.

---

## Architecture

```
IP Camera ──RTSP──► Feed Integrity Monitor      (every frame: freeze/loop/blind)
                             │
                    Tier 1  Motion Gate         drops static frames — ~55% saved
                             │
                    Tier 2  YOLO11 + ByteTrack  detect + persistent track ids
                             │
                    Tier 3  Zones + Risk Engine boundaries, intent, dwell, pacing
                             │
                    Tier 4  YuNet faces         inside person crops only
                             │
                    Tier 5  Hash-chained ledger + WebSocket ──► 3D dashboard
```

Only ~1KB of JSON per event crosses the network — never video. A BOP on a
2G VSAT link can run ten AI-monitored cameras; streaming even one of those to a
central server would saturate it.

---

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/cameras` · `POST` · `DELETE /{id}` | Camera fleet |
| `POST /api/upload` | Ingest recorded footage |
| `GET /api/stream/{id}` | MJPEG video (overlays drawn client-side) |
| `GET/POST /api/zones/{id}` | Boundaries |
| `GET /api/events` | Event log |
| `GET /api/search?q=` | Forensic search |
| `GET /api/ledger/verify` | Chain-of-custody proof |
| `GET /api/stats` | Operational metrics |
| `WS /ws` | Live detections + alerts |

The REST/WebSocket API is the northbound integration path into an existing
command-and-control system.

---

## Measured on this build

Apple Silicon, **CPU only**, 640×480, single camera:

| Metric | Value |
|---|---|
| Inference latency | **~40 ms/frame** |
| Analysed rate | ~24 fps |
| Compute saved by motion gate | **~56%** |
| Alert reduction from cooldown logic | **28 → 5 events** (82%) in a 45s test |
| Chain verification | 100% tamper detection |

Quote the alert-reduction number in the pitch. Judges have heard "95% mAP"
from every team; they have not heard "we cut operator alert load by 82%."

---

## Tuning

Everything lives in `backend/config.py`:

```python
RISK_ALERT_THRESHOLD = 70      # lower = more sensitive
CONF_THRESHOLD = 0.35          # YOLO confidence floor
TARGET_FPS = 12                # inference cap per camera
MOTION_MIN_AREA = 900          # motion gate sensitivity
ZONE_COOLDOWN_S = 15.0         # alert de-duplication
FREEZE_FRAMES_ALARM = 45       # ~3s before declaring a frozen feed
```

Bigger model = better accuracy, more cost: drop `yolo11s.pt` or `yolo11m.pt`
into `models/` and point `YOLO_WEIGHTS` at it. On a CUDA machine, set
`device="cuda"` in `backend/detect.py` for roughly 10× throughput.

---

## What is NOT built yet

Stated plainly, so you are never caught out in Q&A:

- **ANPR** — the PS asks for it. Add YOLO plate detection → PaddleOCR with the
  Indian `XX00XX0000` format. Roughly a weekend.
- **Face *recognition*** — detection works; matching needs an ArcFace/SFace
  embedding gallery. The `identity` field in `backend/faces.py` is the hook.
- **VLM alert verification** — the Tier-4 reasoning layer from your blueprint.
  Qwen2.5-VL-3B, triggered only above the risk threshold.
- **Cross-camera Re-ID** — ByteTrack already carries appearance features;
  persisting them across two cameras is the remaining step.
- **Gun detection** — needs your own fine-tuned weights, as explained above.

Everything else in the problem statement is working.
