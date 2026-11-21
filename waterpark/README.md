# Waterpark — Sunrise Fever

3D-animatie in three.js op de beats van *Sunrise Fever* (145 BPM, 96 maten, 161,9 s).
Vier stokpoppetjes testen een waterpark uit: wenteltrap, rode kamikaze, gele spiraaltube,
blauwe slingerbaan, lazy river met ophaalbrug, en als finale kiept de reuzenemmer op de toren.

Alles in de scène is een **pure functie van de muziektijd** (`renderAt(t)`): geen opgebouwde
state, dus nooit drift. Een trage frame slaat over, en een export rendert elke frame exact op `t = i/fps`.

## De hele film in één keer

```bash
python make_film.py                    # Blender-look (Eevee 1080p) -> waterpark_film.mp4
python make_film.py --look threejs     # three.js-look uit de browser -> waterpark_sunrise_fever.mp4
```

Nodig: Chrome of Edge, Blender (4.2 of nieuwer), ffmpeg in het PATH, en internet (three.js komt van unpkg).
Blender en de browser worden zelf gezocht; anders geef je `--blender <pad>` of `--browser <pad>`.

Wat er gebeurt bij de Blender-look:

1. **Bake** (±40 s): de scène draait onzichtbaar in de browser. Die schrijft `_film/scene.glb` en per frame
   de stand van alles wat beweegt: camera, zon, poppetjes, emmer, brug, fonteinen, lampen, golfslagbad en spetters.
2. **Render**: Blender laadt de scène één keer en rendert elke frame naar `_film/frames/`.
   Afbreken mag: bij een herstart gaat het verder waar het gebleven was.
3. **mp4**: ffmpeg plakt de frames en de muziek samen (H.264 CRF 17, AAC 320k).

Verandert `index.html`, dan wordt de scène vanzelf opnieuw gebakken en gaan de oude frames weg.

| Optie | Wat |
|---|---|
| `--engine eevee\|cycles` | standaard Eevee |
| `--samples 16` | samples per frame |
| `--res 1920x1080` | resolutie |
| `--device gpu` | voor Cycles: eerste beschikbare GPU |
| `--t0 60 --t1 70` | alleen een stuk (seconden) |
| `--only bake\|render` | stoppen na die stap |
| `--rebake` / `--clean` | scène opnieuw bakken / alle frames weggooien |

Twee computers tegelijk laten renderen: zelfde bake (map `_film`) op beide zetten, en op elk een eigen stuk renderen met
`blender -b --python blender/look_still.py -- --film _film --range 0:2400` (en `2400:`). Daarna `python make_film.py` voor de mp4.

## Bekijken

Vanuit de map `animaties`:

```bash
python .claude/tools/devserver.py 8779 waterpark
```

Open http://localhost:8779 en klik om te starten.

| Toets | Wat |
|---|---|
| spatie | pauze |
| ← / → | maat terug / vooruit |
| 1–8 | naar een sectie |
| H | HUD en tijdbalk aan/uit |
| [ / ] | beat-offset −/+ 10 ms |

URL: `?bar=33.5` of `?t=55` opent stilstaand op dat moment.
Debug-camera in de console: `window.__cam = [[x,y,z],[kijkpunt]]` (`null` = normaal).

## 1080p-mp4 uit de browser (three.js-look)

```bash
python .claude/tools/framepipe.py 8780 waterpark waterpark/Sunrise_Fever.mp3 waterpark/waterpark_sunrise_fever.mp4
```

Open http://localhost:8780/?render=1 en voer in de console uit:

```js
await window.__renderVideo(30)        // fps; optioneel (fps, t0, t1)
```

De frames gaan als JPEG rechtstreeks naar ffmpeg (H.264 CRF 17 + AAC 320k). Als het klaar is,
verschijnt `waterpark_sunrise_fever.mp4.done`. ffmpeg moet in het PATH staan.

## Blender-look (realistisch landschap, poppetjes as-is)

**1. Een moment exporteren.** Met de devserver (poort 8779) open, in de console:

```js
await window.__exportBar(46, 'wp_park')     // maat, naam -> waterpark/_snaps/wp_park.glb + .json
```

De `.json` bevat camera, zon en spetters. Materialen krijgen een soortnaam (water, concrete,
slide_red, ...); de poppetjes houden hun eigen materiaal (`fig_*`).

**2. Renderen.** Vanuit `waterpark/blender`:

```bash
blender -b --python look_still.py -- --in ../_snaps/wp_park --out ../_snaps/look_park.png --res 1920x1080 --samples 64 --device gpu
```

Opties:

- `--device cpu|gpu|optix|cuda|hip|metal|oneapi`: met `gpu` wordt de eerste beschikbare gekozen.
- `--tube clear|dome`: de gele buis helemaal doorzichtig (standaard) of met een dichte goot en een glazen dak.
- `--denoise HIGH|BALANCED|FAST`
- `--ladder e,c1,c4`: zelfde scène met Eevee (`e`) en Cycles met een tijdslimiet (`c<N>` seconden). De tijden komen in `<out>_times.json`.
- `--esamples 16`: aantal samples voor Eevee.

**Gemeten op een i3-8145U zonder GPU** (parkoverzicht, per frame):

| Instelling | Per frame | Hele film |
|---|---|---|
| Eevee 540p | 2,7 s | 3,6 u |
| Eevee 1080p | 5,7 s | 7,7 u |
| Cycles 540p, FAST-denoise | 3,5 s | 4,7 u |
| Cycles 1080p, FAST-denoise | 14 s | 19 u |
| Cycles 1080p, HIGH, ruim | ~60 s | 81 u |

Op de CPU kost het ontruisen het meest (23 s per 1080p-frame op HIGH). Met een GPU zakt dat drastisch.

Voor de hele film: zie *De hele film in één keer* hierboven (`make_film.py`).
Gemeten hier: Eevee op 960×540 met 8 samples ±6–12 s per frame, op deze CPU zonder GPU. Met een videokaart gaat het veel sneller.
