const WILD0_SHEET_NAME = "wild0_uploads";
const WILD0_FOLDER_NAME = "WILD0_uploaded_json";

function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, receiver: "WILD0", time: new Date().toISOString() }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const raw = extractPayload_(e);
    const data = JSON.parse(raw);
    const folder = getOrCreateFolder_();
    const file = savePayloadFile_(folder, data, raw);
    const sheet = getOrCreateSheet_();
    ensureHeader_(sheet);
    sheet.appendRow(buildRow_(data, raw, file));
    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, file_url: file.getUrl(), received_at: new Date().toISOString() }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err && err.stack ? err.stack : err) }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

function extractPayload_(e) {
  if (e && e.parameter && e.parameter.payload) return e.parameter.payload;
  if (e && e.postData && e.postData.contents) return e.postData.contents;
  throw new Error("No payload found");
}

function getOrCreateSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(WILD0_SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(WILD0_SHEET_NAME);
  return sheet;
}

function getOrCreateFolder_() {
  const props = PropertiesService.getScriptProperties();
  const existingId = props.getProperty("WILD0_FOLDER_ID");
  if (existingId) {
    try {
      return DriveApp.getFolderById(existingId);
    } catch (err) {
      props.deleteProperty("WILD0_FOLDER_ID");
    }
  }
  const folders = DriveApp.getFoldersByName(WILD0_FOLDER_NAME);
  const folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(WILD0_FOLDER_NAME);
  props.setProperty("WILD0_FOLDER_ID", folder.getId());
  return folder;
}

function savePayloadFile_(folder, data, raw) {
  const participant = safeName_(data.participant_id || "anonymous");
  const version = safeName_(data.version || "unknown_version");
  const stamp = Utilities.formatDate(new Date(), "UTC", "yyyyMMdd_HHmmss_SSS");
  const name = `wild0_${participant}_${version}_${stamp}.json`;
  return folder.createFile(name, raw, "application/json");
}

function ensureHeader_(sheet) {
  const header = [
    "received_at",
    "participant_id",
    "version",
    "mode",
    "upload_reason",
    "upload_status",
    "finished_at",
    "perceived_ease",
    "n_trials_total",
    "n_scored_trials",
    "interpretable_fraction",
    "mean_unique_clicks",
    "payload_bytes",
    "payload_sha256",
    "json_file_url"
  ];
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(header);
    return;
  }
  const current = sheet.getRange(1, 1, 1, header.length).getValues()[0];
  if (current.join("\u0001") !== header.join("\u0001")) {
    sheet.insertRowBefore(1);
    sheet.getRange(1, 1, 1, header.length).setValues([header]);
  }
}

function buildRow_(data, raw, file) {
  const summary = data.summary || {};
  return [
    new Date().toISOString(),
    data.participant_id || "",
    data.version || "",
    data.mode || "",
    data.last_upload_reason || "",
    data.upload_status || "",
    data.finished_at || "",
    data.perceived_ease || "",
    summary.n_trials_total == null ? "" : summary.n_trials_total,
    summary.n_scored_trials == null ? "" : summary.n_scored_trials,
    summary.interpretable_for_K_comparison_fraction == null ? "" : summary.interpretable_for_K_comparison_fraction,
    summary.mean_unique_clicks == null ? "" : summary.mean_unique_clicks,
    raw.length,
    sha256_(raw),
    file.getUrl()
  ];
}

function sha256_(text) {
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, text, Utilities.Charset.UTF_8);
  return digest.map(function(byte) {
    const value = byte < 0 ? byte + 256 : byte;
    return ("0" + value.toString(16)).slice(-2);
  }).join("");
}

function safeName_(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]+/g, "_").slice(0, 80);
}
