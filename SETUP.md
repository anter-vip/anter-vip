# Setup — how this profile goes live

This repo is designed to be your **GitHub profile repo**: a repo named exactly
like your username (`anter-vip/anter-vip`), whose `README.md` renders on your
profile page.

## 1. Rename / create the repo

```bash
# the local folder can keep any name; the REMOTE must be username/username
git remote set-url origin https://github.com/anter-vip/anter-vip.git
# (or create github.com/new -> repository name MUST equal your username)
```

## 2. Push everything

```bash
git add -A
git commit -m "generative profile v1 — algorithms, not templates"
git push -u origin main
```

## 3. Run the generators once (locally or via Actions)

Local dry-run (uses the date as seed, no token needed — falls back to
synthetic contribution data):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd generators
for f in hero_flowfield terminal_intro kmeans_skills sorting_visualizer \
         life_contributions stats_dashboard force_graph_stack project_cards \
         footer_line; do ../.venv/bin/python $f.py; done
```

On GitHub: **Actions → generate-art → Run workflow**. It regenerates every
asset with live API data (`GITHUB_TOKEN` is provided automatically — no
secrets to add) and commits only if something changed.

## 4. Snake

**Actions → snake → Run workflow.** Platane/snk writes `snake.svg` and
`snake-eating.svg` to the `output` branch, which the README reads via
`raw.githubusercontent.com/anter-vip/anter-vip/output/assets/...`.

## 5. Daily cron

`generate.yml` runs at 05:17 UTC every day; `snake.yml` at 05:40. The art is a
deterministic function of the date, so the profile visibly changes each day
while remaining reproducible.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| An SVG doesn't animate | GitHub sometimes caches; open the raw asset URL directly, or hard-reload |
| `stats.svg` shows "offline fallback" | REST rate limit hit — Actions token fixes it; cron reruns next morning |
| A generator crashes | workflow is fail-soft: previous day's asset stays, warning in the run log |
| Snake image 404 | run `snake.yml` manually once to create the `output` branch |
