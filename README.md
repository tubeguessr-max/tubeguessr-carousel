# TubeGuessr daily TikTok carousel

Every day a GitHub Action picks a random image from each of your three Google Drive folders,
picks a random station, renders the 3 slides in TikTok's text style, and sends them to your
TikTok **drafts** via PostPeer. You open TikTok, add a sound, and publish.

Slide 1 = hook + arrow. Slide 2 = "I'm at a station with [line pills]... Where am I??".
Slide 3 = "[Station]!" + your App Store CTA and screenshot.

## One-time setup

**1. Add two files**
- `fonts/TikTokSans.ttf`: download TikTok Sans from Google Fonts (variable font), rename it to this.
- `assets/app-store.png`: crop of the App Store card from your slide 3 (about 606px wide).

**2. GitHub**
Create a **public** repo (the slides are served from it) and push this folder. Then in
Settings > Secrets and variables > Actions, add the secrets listed in step 5.
Only the code and the App Store image are public. Your Drive photos and keys are not.

**3. Google Drive access (free)**
1. console.cloud.google.com: create a project, enable the **Google Drive API**.
2. IAM & Admin > Service Accounts: create one, then Keys > Add key > JSON. Download it.
3. Share each of your 3 Drive folders with the service account's email (Viewer is enough).
4. Folder ID = the last part of the folder's URL.
If slides 2 and 3 use the same folder, the script picks two different images from it.

**4. PostPeer**
Sign up, connect your TikTok account, copy your access key, and get your account ID
(Integrations page, or `GET https://api.postpeer.dev/v1/connect/integrations`).

**5. GitHub secrets**
| Secret | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | full contents of the JSON key file |
| `DRIVE_FOLDER_SLIDE1` / `2` / `3` | the three folder IDs |
| `POSTPEER_API_KEY` | PostPeer access key |
| `POSTPEER_ACCOUNT_ID` | your connected TikTok account ID |

**6. Test**
Actions tab > "Daily TubeGuessr carousel" > Run workflow. A draft should land in your TikTok inbox.

## Things to check
- `data/stations.json`: I wrote these from memory. **Check every station's lines against TfL's
  site before relying on them**, and add more stations in the same format.
- Photos must be jpg, png or webp (iPhone HEIC isn't supported; export as JPEG).
- Run time: edit the cron line in `.github/workflows/daily.yml` (it's UTC).
- If a run fails, GitHub emails you. A day with no draft means check the Actions tab.
- GitHub can pause scheduled workflows in repos with no activity for 60 days. The daily
  push to the `slides` branch should count, but glance at the Actions tab now and then.
- Hooks live in `data/hooks.json`; the caption is in `config.py`.
- Text weight (Classic vs Bold look) is `FONT_WEIGHT` in `config.py`.

## Preview on your computer
```
pip install -r requirements.txt
python -m playwright install chromium
python main.py check
python main.py render --local ./some-folder-of-photos
```
Slides appear in `out/`.
