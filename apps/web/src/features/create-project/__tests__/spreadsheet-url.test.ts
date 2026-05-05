import { describe, expect, it } from "vitest";

import { extractSpreadsheetId } from "../spreadsheet-url";


const ID = "1GOnAbCDeFgHiJkLmNoPqRsTuVwXyZ-_0123456789";


describe("extractSpreadsheetId", () => {
  it("matches a clean URL without /u/N/", () => {
    const url = `https://docs.google.com/spreadsheets/d/${ID}/edit`;
    expect(extractSpreadsheetId(url)).toBe(ID);
  });

  it("matches a URL with /u/0/ (first signed-in account)", () => {
    const url = `https://docs.google.com/spreadsheets/u/0/d/${ID}/edit`;
    expect(extractSpreadsheetId(url)).toBe(ID);
  });

  it("matches a URL with /u/1/", () => {
    const url = `https://docs.google.com/spreadsheets/u/1/d/${ID}/edit`;
    expect(extractSpreadsheetId(url)).toBe(ID);
  });

  it("matches a URL with /u/2/ and ?usp=drive_fs query string", () => {
    const url = `https://docs.google.com/spreadsheets/u/2/d/${ID}/edit?usp=drive_fs`;
    expect(extractSpreadsheetId(url)).toBe(ID);
  });

  it("returns null for unrelated text", () => {
    expect(extractSpreadsheetId("not a sheet URL")).toBeNull();
  });

  it("returns null for non-Sheets Google URL", () => {
    expect(
      extractSpreadsheetId(`https://docs.google.com/document/d/${ID}/edit`),
    ).toBeNull();
  });
});
