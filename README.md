# Harbour Wind

Hong Kong's weather drawn as a living fluid. Live readings from the Hong Kong Observatory (HKO) steer hundreds of thousands of GPU particles across the territory, leaving long glowing trails. The piece is in the spirit of Refik Anadol's data paintings.

![Harbour Wind rendering live HKO readings: 15:50 HKT, 15 Nov 2026, 30 wind stations, mean 8 km/h from the south](docs/screenshot.jpg)

## See it

**Live:** https://raidianblaster.github.io/harbour-wind/

**Locally:**

```
python3 serve.py
```

Then open http://localhost:8000. You need Python 3 and a WebGL2 browser (any recent Chrome, Safari or Firefox). There is nothing to install and no build step. You can also open `index.html` directly; it reads the same published data as the live site.

**Controls:** drag to stir the flow, tap to hide the overlay, and use the **Controls** button for palette, particle count, wind, turbulence, trails, glow, brightness, the station overlay, a faint coastline map (off by default), and live mode.

## How the data becomes the image

| HKO reading | What it drives |
|---|---|
| 10-minute mean wind direction and speed, 30 stations | The flow field particles follow |
| Gust to mean ratio per station | A pulse: local flow surges between mean and gust strength |
| Air temperature, ~39 stations | Particle colour, from cool (mountain tops) to warm (lowland towns) |
| Relative humidity | Extra swirling turbulence |

Station readings are blended into a continuous field over a map of Hong Kong. Every 2 minutes the page checks HKO for new readings. When a new 10-minute reading lands, the old field dissolves into the new one over 30 seconds.

## Where the live data comes from

HKO publishes its readings as open data, but the CSV files don't allow web pages on other sites to read them (no CORS header). The page needs three of them:

- [10-minute wind](https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_10min_wind.csv)
- [Temperature](https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature.csv)
- [Humidity](https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_humidity.csv)

There are two ways the page gets them, and it tries them in this order:

1. **Local relay:** `serve.py`, a small standard-library server on localhost. It caches each feed for 60 seconds and keeps serving the last good copy if HKO is down.
2. **Data branch:** a scheduled GitHub Action ([`hko-data.yml`](.github/workflows/hko-data.yml)) copies the three files to the [`data` branch](https://github.com/raidianblaster/harbour-wind/tree/data) about every 10 minutes, and the page reads them from there. GitHub's scheduler often runs late, so the public site can lag HKO by 10 to 30 minutes. If the readings are more than an hour old, the page shows their age instead of "live".

## How it's built

A single `index.html`, plain WebGL2, no libraries:

- **Field:** station readings are interpolated (inverse-distance weighting) onto a 128×97 grid and uploaded as a float texture.
- **Particles:** advected on the GPU with transform feedback, plus curl noise for turbulence.
- **Trails and glow:** a fading trail buffer and a two-level bloom, finished with a tonemap, vignette and film grain.

## Notes

- Station positions are hand-approximated. They're accurate enough for art, but not for analysis.
- So far it has only been tested with software rendering. Real-GPU testing on Mac and iPhone is still to do.
- Data: [Hong Kong Observatory](https://www.hko.gov.hk/) open data. This project is not affiliated with HKO.
- Coastline: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL. Simplified and embedded by [`tools/coastline.py`](tools/coastline.py).
