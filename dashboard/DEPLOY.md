# Deploy guide — Cloudflare Pages with Access

The dashboard is a static export. `npm run build` produces `out/`, which gets
uploaded to Cloudflare Pages. **The deployment contains gold answers, run
artifacts, and other data the repo's `.gitignore` treats as private**, so it
must go behind Cloudflare Access before sharing the URL.

## One-time setup

1. **Cloudflare account.** Create a free account at https://dash.cloudflare.com
   if you don't have one.

2. **Authenticate wrangler.** From this directory:
   ```bash
   npx wrangler login
   ```
   Opens a browser tab; click "Allow" to grant CLI access to your account.

3. **First deploy.** Creates the Pages project, asks for the project name
   (default in `wrangler.jsonc` is `capable-bench-dashboard`):
   ```bash
   npm run deploy
   ```
   Output ends with a `*.pages.dev` URL. **Don't share this URL yet** — it's
   publicly resolvable until Access is in front of it.

## Lock it down with Cloudflare Access

This is done in the Cloudflare dashboard UI, not via wrangler.

1. Open https://one.dash.cloudflare.com (Zero Trust dashboard). If this is your
   first Zero Trust use, you'll be prompted to pick a team domain
   (`<team>.cloudflareaccess.com`) and the **Free** plan (50 users).

2. **Access → Applications → Add an application → Self-hosted.**

3. **Application configuration**
   - Application name: `Capable Bench Dashboard` (or whatever)
   - Session duration: 24 hours (or your preference)
   - **Application domain**: paste the `*.pages.dev` hostname from the deploy
     output, with `*` as the wildcard subdomain — e.g.
     `capable-bench-dashboard.pages.dev` with path `*`.
     (If you later attach a custom domain, add that domain too.)

4. **Identity providers**: enable at least one. Easiest is the built-in
   **One-time PIN** provider — it emails a 6-digit code to the user's address
   on each login, no Google/SSO setup needed. For a team SSO flow, add Google
   / GitHub / Okta under Settings → Authentication first.

5. **Policies → Add a policy**
   - Policy name: `Allow team`
   - Action: **Allow**
   - Configure rules — Selector: **Emails ending in** → `@yourdomain.com`,
     OR Selector: **Emails** with an explicit allowlist of addresses.

6. Save. The Access challenge propagates in ~30 seconds.

7. **Verify.** Open the `*.pages.dev` URL in an incognito window. You should
   see Cloudflare Access's login screen, not the dashboard. Sign in with an
   allowed email → dashboard loads.

## Subsequent deploys

```bash
npm run deploy
```

`npm run build` re-bakes everything: `dashboard.json`, `run-artifacts/*.json`,
and `finding-files/*` are regenerated from the live repo state every time.
Then wrangler uploads the `out/` directory. Builds take ~10 seconds locally
and upload in ~30 seconds for the current ~19 MB of data.

The Access policy stays in front of all future deploys automatically — the
domain-level rule covers every preview and production URL.

## What the deployment exposes

The static bundle bakes in everything the dashboard surfaces:

- `dashboard.json` — task metadata, gold answers, latest run grades, calibration
- `run-artifacts/<task>/<runId>.json` — stdout/stderr/trace/answer text per run
- `finding-files/<id>/...` — non-README files in `docs/findings/` (images,
  trace files, CSVs, YAMLs)

If you ever need to scrub something specific before sharing externally, edit
the bake script (`scripts/bake-static.ts`) to filter it out and redeploy.

## Troubleshooting

- **`wrangler pages deploy` says "project not found"** — the first deploy
  creates it; pass `--project-name=capable-bench-dashboard` explicitly if it
  fails to read `wrangler.jsonc`.
- **Access challenge doesn't appear** — give it 30–60 seconds after saving
  the policy. Make sure the application domain matches the `*.pages.dev`
  hostname exactly (no `https://`, no trailing slash).
- **Want a custom domain** — Pages → your project → Custom domains → add
  domain. Add the same domain to the Access application's domain list so the
  policy covers it.
