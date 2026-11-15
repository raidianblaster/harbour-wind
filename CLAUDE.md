# Harbour Wind

Data-driven fluid artwork in the style of Refik Anadol: live Hong Kong Observatory (HKO) weather drives a GPU particle flow field rendered with long trails and bloom. Single self-contained `index.html` (WebGL2, no build step, no dependencies beyond Google Fonts).

Started in a claude.ai chat on 12 Nov 2026. Published version: https://claude.ai/artifact/K9nUkyF35PJ26vTfk3M1mg (private to the owner). This folder is now the source of truth.

## Run it

For live data, use the bundled relay (a plain static server will not do; see Data source):

```
python3 serve.py   # then open http://localhost:8000
```

Opening `index.html` directly (file://) skips the relay and reads the `data` branch; the claude.ai artifact can't fetch at all and stays on the embedded snapshot.

## Data → visual mapping (the core idea)

| Data (HKO) | Drives |
|---|---|
| 10-min mean wind direction + speed, 30 stations | Velocity field (flow) |
| Max gust / mean ratio per station | Pulse: field strength oscillates between mean and gust via noise |
| Air temperature, ~39 stations | Particle colour (palette position) |
| Mean relative humidity | Extra curl-noise turbulence (multiplier 0.7 + RH·0.006) |

- Wind directions are "from" bearings. Flow vector = -(sin b, cos b) · speed (east, north).
- Stations with direction `Variable` or `N/A` contribute speed/gust but no vector. `Calm` = zero vector.
- Temperature normalised around the median: `t = (T - (median - 3)) / 6`, clamped 0..1. Mountain stations (Tai Mo Shan, Tate's Cairn, The Peak) read cold blue, Yuen Long warm amber.

## Data source

- Current snapshot is embedded in `SNAPSHOT` in `index.html`: HKO readings at 09:30 HKT, 12 Nov 2026.
- Text page: https://www.hko.gov.hk/textonly/v2/forecast/text_readings_e.htm
- Machine-readable wind CSV (updated every 10 min): https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_10min_wind.csv
  Columns: datetime (YYYYMMDDHHMN), station, 10-min mean direction (compass / Calm / Variable / N/A), mean speed km/h, max gust km/h.
- Current weather JSON (temperature, humidity, rainfall): https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=en
- CORS (checked 15 Nov 2026): the regional-weather CSVs (`latest_10min_wind.csv`, `latest_1min_temperature.csv`, `latest_1min_humidity.csv`) send NO `Access-Control-Allow-Origin`, so browsers can't read them directly; the `rhrread` JSON does send `*`. Hence `serve.py`: stdlib server on 127.0.0.1 that relays the three CSVs at `/hko/wind|temp|rh` (60 s cache, serves stale if HKO is down).
- Public site: https://raidianblaster.github.io/harbour-wind/ (GitHub Pages from `main` root; landing page lives in the separate `raidianblaster.github.io` repo). Pages can't run `serve.py`, so the `HKO data` workflow (`.github/workflows/hko-data.yml`, cron `7,37 * * * *`, i.e. every 30 min; was every 10, cut to reduce load) force-pushes the three CSVs as a single orphan commit to the `data` branch; the page reads them from raw.githubusercontent.com (CORS `*`, CDN max-age 300). Source order in `readAll()`: local relay, then data branch. Readings older than `STALE_MIN` (90) show their age instead of "live". Cron runs are best-effort (often 5 to 20 min late) and GitHub pauses schedules after 60 days without repo activity.
- Live mode: page polls every 5 min (`POLL_MS`), and when the wind CSV timestamp changes it crossfades the field over 30 s (6 s for the first live load, replacing the snapshot). Blend is CPU lerp of the field array + `texSubImage2D` each frame, eased with smoothstep; RH is lerped too. Fade time is sim time (dt capped at 1/20 s), so it pauses with Pause and runs slow on software GL. Pasting readings or "Back to snapshot" switches live off.
- The artifact version can't fetch (artifact CSP), so the paste-to-refresh parser (`parseHKO`) for the text page stays as the fallback.
- Coastline overlay (Controls > Coastline, off by default): `COAST` in `index.html` is OSM `natural=coastline` for the bbox, stitched, clipped, Douglas-Peucker simplified to 35 m, islets under 0.6 km dropped, polyline-encoded at 1e-4 deg (107 lines, ~5.2k points, 13 KB). Lines are separated by spaces because polyline output uses ASCII 63-126, which includes `|` and `\`. Regenerate with `tools/coastline.py` (instructions in its docstring). Drawn on the 2D overlay canvas at 0.75 px, alpha 0.3 (owner's choice; 0.17 was too faint). These are open lines, not land polygons, so a land/water mask would need closing against the bbox first. ODbL: keep the attribution in the panel and README.
- Station coordinates in `STATIONS` are hand-approximated [lat, lon]. Good enough for art, not survey-grade. Replace with HKO's official station list if precision matters.

## Tuning notes (learned the hard way)

- First pass was badly overexposed. Particle alpha is now `0.075 · density · ((1-trail)/0.05)^0.7`, where density = pixels/(count·5) clamped 0.25..4. Bloom weights 0.55 (1/4) and 0.9 (1/8).
- Respawning off-screen particles at random positions starved the upwind (east) edge, leaving a dark band. Wrapping fixed it; resetting age on wrap brought the band back (fade-in), so age is preserved.
- Default particle count: 150k on touch devices, 300k on desktop. Render scale capped at 1.5× DPR.
- Only tested in headless Chrome with SwiftShader (software GL). Needs real-GPU testing on Mac and iPhone.
- Map fit is "cover": landscape screens show the full width, portrait phones show a central slice (roughly Tsing Yi to Kai Tak).

## Ideas / next steps

- Time-lapse: replay a day of historical readings (data.gov.hk keeps history).
- Latent-space layer (the Anadol signature): CLIP embeddings of a Hong Kong photo set, UMAP to 2D, used as particle colour or attractor field.
- Coastline mask (land vs water behaviour) from an HK boundary GeoJSON.
- Frame export to video (ffmpeg, H.264).
- Port to TouchDesigner for installation-grade output.

## Working preferences

- Owner prefers direct, technically honest assessments and dense structured output.
- Check with the owner before building anything substantial; propose first.
- Avoid em dashes in written output.
