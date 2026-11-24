# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/Poorya0128/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/Poorya0128/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A one-page newspaper summing up Monday 23 November 2026 in 35 stories across 10 regions and 15 topics: 3 lead stories, 10 picture cards, a 22-story list, a world map with 34 pins, a "What we don't know yet" box and a date check. Drawn entirely with Pillow (no photos); the map coastlines come from Natural Earth.

## Run it

```sh
python3 main.py
```

`main.py` (standard library only) validates the pre-rendered `entry.png` (1024x1024, under 1 MiB) and copies it to `$MAKEFUN_OUTPUT_DIR`. `build.py` regenerates the image with Pillow; `prep_map.py` downloads the Natural Earth 1:110m land file from jsDelivr and converts it to `world_land.json`. Map data: Natural Earth (public domain).

---

<sub>Entered on [make.fun](https://make.fun/?ref=yp1rdj4t&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>
