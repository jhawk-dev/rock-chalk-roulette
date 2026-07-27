# Rock Chalk Roulette

A single self-contained HTML page — draft a Frankenstein Kansas Jayhawks basketball roster (2 Guards, 2 Forwards, 1 Center) from real player seasons spanning 1945–2026. No build step, no dependencies; fonts and data are inlined directly in `index.html`.

## Deploying on Netlify

1. Netlify dashboard → **Add new site** → **Import an existing project** → select this repo.
2. Build settings: leave the **build command** blank and set **publish directory** to the repo root (`.`) — there's nothing to build.
3. Deploy. Any future commit to `main` will redeploy automatically.
4. Add your custom domain under **Domain management** and follow Netlify's DNS instructions.
