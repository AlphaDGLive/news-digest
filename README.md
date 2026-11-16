# News Digest Desk

A free dashboard where you create thematic news digests in a dialog box and schedule them.
For example: "every day at 07:30, all MRO news on the 747 fleet worldwide" or "all mentions of Sharjah".

- **Website:** free on GitHub Pages at `https://YOUR-NAME.github.io/news-digest/`
- **Scheduler:** free GitHub Actions job that checks every 15 minutes and produces each digest at its own time
- **News source:** Google News search (many countries and languages), with duplicates removed
- **Cost:** 0. No server, no paid domain, no paid support.

## One-time setup (about 10 minutes)

1. **Create a free GitHub account** at github.com, if you don't have one.
2. **Create a repository.** Click **New repository**, name it `news-digest`, set it to **Public** (Pages and Actions are free for public repos), then click **Create**.
3. **Upload the files.** On the new repo page, click **uploading an existing file** and drag in *everything* from this folder, including the hidden `.github` folder. Then click **Commit changes**.
   - The `.github` folder may be hidden on your computer. If it won't upload, create the file on GitHub directly: **Add file → Create new file**, name it `.github/workflows/digests.yml`, and paste in its contents.
4. **Turn on the website.** Go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
5. **Allow the job to save results.** Go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**, then click Save.
6. **Run it once.** Go to **Actions → Digests → Run workflow**, type `all`, and click **Run**. After about 2 minutes your site is live at `https://YOUR-NAME.github.io/news-digest/`.
7. **Let the dashboard save digests.** Create a token at GitHub → your avatar → **Settings → Developer settings → Fine-grained tokens → Generate new token**:
   - Repository access: **Only select repositories → news-digest**
   - Permissions: **Contents: Read and write**, **Actions: Read and write**
   - Copy the token, open your site, click **⚙︎ Settings** and paste it in. The token is stored only in that browser.

## Daily use

- **＋ New digest** opens a dialog. Give it a name, then describe the topic as lines:
  - Each line is one concept. Separate synonyms with commas.
  - An article must match every line.
  - Example for 747 MRO:
    ```
    747, B747, Boeing 747, 747-400, 747-8
    MRO, maintenance, heavy check, C-check, overhaul, freighter conversion
    ```
  - Example for Sharjah: `Sharjah, الشارقة`
  - Use **Test this search on Google News** to check the results before saving.
- Set the time (several are allowed, e.g. `07:30, 18:00`), days, time zone and news editions.
- **▶ Run now** produces a digest immediately (ready in about 1–3 minutes).
- Articles that weren't in the previous digest are highlighted as **new**. The dropdown shows past digests (the last 60 are kept).
- **✎ Edit** changes a digest, pauses it, or deletes it.

## Good to know

- GitHub's free scheduler can start 5–20 minutes late at busy times. A 07:30 digest usually appears between 07:30 and 07:50. If a run is missed, the next check catches up automatically.
- Coverage is whatever Google News indexes. Most trade press is included (FlightGlobal, Aviation Week, Simple Flying, AeroTime, Gulf News, Khaleej Times, etc.). Paywalled articles show their headline only.
- Advanced: under **Advanced** in the dialog you can write a raw Google News query, e.g.
  `747 (MRO OR "heavy check") site:aviationweek.com`.

## Files

| File | Purpose |
|---|---|
| `index.html` | The dashboard (dialogs, digest list, reader) |
| `digests.json` | Your digests and schedules (edited by the dashboard) |
| `scripts/build_digests.py` | Fetches the news and builds the digests |
| `.github/workflows/digests.yml` | Schedule: runs the script every 15 min, then publishes the site |
| `data/` | Produced digests (`latest.json`, archive, `index.json`) |
