# WILD-0 Upload Receiver

`occam.world` is static GitHub Pages, so it cannot store data by itself.
Use a Google Sheet + Apps Script receiver for lightweight calibration runs.

## One-time setup

1. Create a new Google Sheet, for example `WILD0 uploads`.
2. Open `Extensions -> Apps Script`.
3. Paste the contents of `google_apps_script_receiver.gs`.
4. Save.
5. Click `Deploy -> New deployment`.
6. Select type `Web app`.
7. Set:
   - Execute as: `Me`
   - Who has access: `Anyone`
8. Deploy and copy the `/exec` Web App URL.

## Study link

Use:

```text
https://occam.world/wild0/?mode=B0.6&upload_url=YOUR_WEB_APP_EXEC_URL&upload_mode=no_cors_form
```

If the URL contains special characters, encode it first and put the encoded
value after `upload_url=`.

The page uploads checkpoints after each round, after task completion, after
the final question, and attempts a last `sendBeacon` upload if the tab closes.

## Where data go

- The sheet tab `wild0_uploads` receives one row per upload event.
- Full JSON files are saved into a Drive folder named `WILD0_uploaded_json`.
- The sheet row includes the Drive file URL and a SHA-256 hash of the payload.

## Notes

The Google Apps Script mode uses a no-CORS form POST. The browser can confirm
that the request was sent, but cannot read the receiver response. This is
acceptable for lightweight calibration. For paid Prolific collection, keep the
manual JSON download button as a fallback and check the sheet/Drive after the
first pilot participants.
