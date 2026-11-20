# Maanlicht op het plein — Sinterklaas

Canvas-animatie die is opgebouwd vanuit de visuele template `ref.png`
(1672 × 941). Het toneel heeft exact die maat, zodat je de template er
altijd overheen kunt leggen.

## Openen

Dubbelklikken op `index.html` werkt. Voor de snapshot-tool: start de
`sinterklaas` preview (`.claude/launch.json`, poort 8778).

| Toets / knop | Wat |
|---|---|
| spatie / ❚❚ | pauze |
| R / ↺ | opnieuw |
| ← → | 1 s terug/vooruit |
| O / `ref` | template vergelijken: uit → 50% erover → linkerhelft → volledig |
| C / `3D` | draaischijf: alle personages los, ronddraaiend |

URL-parameters: `?p=0.25` (start op dat deel van de lus), `&pause`, `&o=1` (overlay), `&c` (draaischijf).

## Bestanden

- `core.js` — hulpjes, toneel/schaal, cachelagen (met eenmalige kleurcorrectie), gloed- en bladsprites
- `puppet3d.js` — mini-3D voor canvas 2D: skelet van nodes + vormen
  (ellipsoïde `E`, capsule `C`, afgeknotte kegel `F`, doos `B`, kaart `K`,
  omslag/lap stof `W`, buis `T`), orthografische projectie, schilders-sortering,
  belichting en cartoon-omlijning
- `characters.js` — Sinterklaas, Piet (2 varianten: zak / pakje) en het paard, elk met `pose(st)`
- `town.js` — statisch decor: lucht, maan, huizen, dak, plein, fontein, kraam, lantaarns
- `anim.js` — alles wat beweegt + tijdlijn + lus + bediening

## Personages: Blender → three.js

De personages zijn echte 3D-modellen met skelet en zachte gewichten:

1. `blender/build_characters.py` bouwt Sint, Piet (zak), Piet (pakje) en het paard
   uit gladde draaivormen, buizen en bollen, en exporteert ze naar `models/*.glb`.
2. `blender/pack.py` pakt ze in tot `models/chars_glb.js` (base64), zodat
   dubbelklikken op `index.html` blijft werken.
3. `chars3d.js` rendert ze met three.js (r147, via CDN) per figuur in een uitsnede.
   `sprite.js` zet ze in de 2D-scène, met één omlijning om het silhouet en randlicht.
4. `poses.js` zet de gewrichten: loopcyclus, zwaaien, naslingerende mantel en pluim.

Modellen opnieuw bouwen:

```bash
"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python blender/build_characters.py -- models
```

```bash
python blender/pack.py models
```

Voorvertoning in Blender (4 aanzichten per figuur):

```bash
"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python blender/preview.py -- models _snaps/bl
```

Als three.js niet laadt (bijvoorbeeld offline), valt de scène terug op de oude
2D-poppen uit `puppet3d.js` en `characters.js`.

## Volledige Blender-scène (richting eindfilm)

Het hele tafereel staat ook als 3D-scène in Blender, op exact de compositie van
de template. `bl_lib.S2W(px, py, diepte)` rekent een templatepixel plus diepte om
naar een 3D-positie.

- `blender/bl_lib.py` — camera, meshhulpjes, procedurele materialen (natuursteen,
  baksteen, dakpannen, keien, hout, schors, ramen met gordijnen, herfstbladeren)
- `blender/scene_town.py` — decor: gebouwen, ramen met stenen bogen, bloembakken,
  fontein, kraam met lichtsnoer, lantaarns, tonnen, pakjes, vlaggen, banier,
  boom met bladeren, kinderkopjes via geometry nodes
- `blender/poses.py` — dezelfde poses als `poses.js`, toegepast op de Blender-skeletten
- `blender/render_still.py` — bouwt alles, belicht en rendert met Cycles, met een transparante lucht
- `blender/post.py` — lucht, wolken, sterren en maan erachter, plus gloed, kleurcorrectie en vignet

Een beeld renderen (op deze laptop ~2,5 min bij 75%):

```bash
"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python blender/render_still.py -- --out _snaps/bl_still.png --res 75 --samples 24
```

```bash
python blender/post.py _snaps/bl_still.png _snaps/bl_post.png
```

`--border x0,y0,x1,y1` rendert alleen een uitsnede (in templatepixels), en `--save scene.blend` bewaart de scène.

## De film: vier kanten van het plein (Blender)

`blender/film.py` bouwt het hele plein rondom en rendert een cyclus van 94 s. De
camera staat midden op het plein en draait na elke scène 90° naar rechts:

| tijd (s) | kant | wat er gebeurt |
|---|---|---|
| 0–36 | noord (template) | Sint te paard en de Pieten over het dak, sprong in de schoorsteen |
| 39–54 | oost: stadhuis met klok | Sint rijdt over het plein, Piet strooit pepernoten, Piet springt een pirouette |
| 57–73 | zuid: kade met de pakjesboot | Piet sjouwt een pakje over de loopplank naar de stapel, Sint wuift naar de boot |
| 76–91 | west: banketbakkerij | Piet klimt via de ladder naar een raam en geeft het pakje af, Sint wacht beneden |

Tussen de scènes (36–39, 54–57, 73–76, 91–94) draait de camera.

- `blender/scene_sides.py` — oost-, zuid- en westkant en de hoeken. Elke kant is
  gebouwd in templatepixels, alsof de camera naar het noorden kijkt, en daarna om
  het midden van het plein gedraaid.
- `blender/film.py` — personages, tijdlijnen per scène (scène 1 = de tijdlijn uit
  `anim.js`), paslengtes, camera en de renderlus. Vóór het renderen worden alle
  stilstaande objecten samengevoegd (~15.000 → ~275), wat het renderen
  ongeveer vijf keer sneller maakt.
- `blender/post_frames.py` — een 360°-lucht die meedraait met de camera, optioneel
  gloed (`--bloom`), en daarna de mp4.

Proefversie (Workbench, snel, ~1,7 s per beeld):

```bash
"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python blender/film.py -- --out _film/proef --engine workbench --res 50 --step 2
```

```bash
python blender/post_frames.py _film/proef --fps 12.5 --mp4 film_proef.mp4
```

Eindversie (Cycles, zwaar; bedoeld voor een snellere computer, te verdelen met `--start/--end`):

```bash
"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python blender/film.py -- --out _film/final --engine cycles --res 100 --samples 64
```

```bash
python blender/post_frames.py _film/final --bloom --fps 25 --mp4 film.mp4
```

### Renderen op een andere (snellere) machine

Nodig: [Blender 5.3](https://www.blender.org/download/), Python 3 met Pillow
(`pip install pillow`) en ffmpeg. Er zijn geen andere bestanden nodig: `film.py`
bouwt het hele plein en de personages zelf op.

```bash
git clone https://github.com/kgdivw/animaties.git
```

```bash
cd animaties/sinterklaas
```

```bash
blender -b --python blender/film.py -- --out _film/final --engine cycles --res 100 --samples 64 --device gpu
```

- `--device gpu` zoekt zelf een GPU (OPTIX/CUDA voor NVIDIA, HIP voor AMD, METAL op een Mac,
  ONEAPI voor Intel) en valt terug op de CPU. In de log staat welke GPU gebruikt wordt.
- De film telt 2350 frames (94 s × 25 fps). Vóór het eerste frame voegt het script
  ~15.000 objecten samen; dat duurt enkele minuten.
- Onderbroken? Herstart met `--start N` (N = eerste ontbrekende frame); `yaw.json` wordt aangevuld.
- Verdelen over meerdere machines: `--start 0 --end 1200` op de ene, `--start 1200` op de andere,
  en daarna alle `f_*.png` en beide `yaw.json`-bestanden samenvoegen in één map
  (de sleutels in `yaw.json` zijn framenummers, dus de inhoud gewoon samenvoegen).
- Op deze laptop: ~10 s per frame op 25% met 16 samples (`--res 25 --samples 16`).

Daarna lucht, gloed en mp4 (ffmpeg moet in het pad staan, of zet `FFMPEG=/pad/naar/ffmpeg`):

```bash
python blender/post_frames.py _film/final --bloom --fps 25 --mp4 film.mp4
```

## Wat beweegt los

- **Personages (3D, kunnen draaien):** Sint, twee Pieten, het paard
- **Wind:** boomtakken + ~900 bladeren, vallende bladeren, vlaggetjeslijnen,
  banier, luifelranden, Piet-veren, Sints mantel, paardenstaart
- **Overig:** fonteinwater + rimpels, schoorsteenrook, roetwolk, flikkerende
  lantaarns, twinkelende sterren

## Tijdlijn (48 s)

- 0.03–0.16 Sint, Piet (pakje) en Piet (zak) klimmen achter de nok omhoog
- **0.25 heldenmoment:** exact de opstelling van de template (Piet 800, Piet 930, Sint 1060)
- 0.30–0.50 Sint draait naar de kijker en zwaait; het paard kijkt op, knikt en stampt
- 0.38–0.63 de Pieten springen op de schoorsteen en zakken erin (roetwolk, zolderraam licht op)
- 0.72–0.85 ze veren er weer uit en lopen terug; Sint volgt
- 0.90–1.00 iedereen klimt achter de nok weg → naadloze lus

## Schimmen achter de ramen

Als de Pieten in de schoorsteen zijn, zie je ze als silhouet achter de verlichte
ramen (`drawHouseSilhouettes` in `anim.js`). Eerst plonzen ze in het zolderraam
van de grote dakkapel, daarna lopen ze langs de benedenramen: Piet met het pakje
zet het op de vensterbank, en Piet met de zak zwaait. De silhouetten zijn dezelfde
3D-modellen, donker en iets onscherp gerenderd, en alleen binnen de ramen
zichtbaar (`Sprite.draw` met `silhouette`).

## MP4 maken

In de console van de geopende pagina (via de `sinterklaas`-preview):

```js
SK.record(25, 0, 48)     // 1200 frames → _snaps/rec_0000.jpg …
```

Daarna:

```bash
ffmpeg -y -framerate 25 -i _snaps/rec_%04d.jpg -vf "crop=1672:940:0:0" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p sinterklaas.mp4
```

## Vergelijken met de template (dev)

In de console: `await SK.snap('a.png', 0.25)` schrijft een render op
toneelmaat naar `_snaps/`. Daarna:

```bash
python .claude/tools/compare.py a.png cmp.png 740 80 1460 330
```

geeft template en render onder elkaar voor die uitsnede.
