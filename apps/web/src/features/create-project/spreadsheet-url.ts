const SPREADSHEET_URL_REGEX =
  /docs\.google\.com\/spreadsheets\/(?:u\/\d+\/)?d\/([a-zA-Z0-9_-]+)/;


export function extractSpreadsheetId(text: string): string | null {
  const match = text.match(SPREADSHEET_URL_REGEX);
  return match ? match[1] : null;
}
