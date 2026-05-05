export type CreateProjectStep =
  | "idle"
  | "awaiting_number_confirmation"
  | "awaiting_spreadsheet"
  | "parsing_spreadsheet"
  | "showing_validation"
  | "awaiting_validation_decision"
  | "awaiting_metadata"
  | "creating"
  | "success"
  | "error";


export interface Issue {
  code: string;
  message: string;
  field?: string;
  value?: unknown;
}


export interface ValidationResult {
  ok: boolean;
  errors: Issue[];
  warnings: Issue[];
}


export interface ProjectMetadata {
  cliente: string;
  empreendimento: string;
  cidade: string;
  estado?: string;
}


export interface CreateProjectState {
  step: CreateProjectStep;
  suggestedNumber?: number;
  confirmedNumber?: number;
  spreadsheetFileName?: string;
  spreadsheetId?: string;
  validationResult?: ValidationResult;
  metadata?: ProjectMetadata;
  errorMessage?: string;
  finalResult?: CreateProjectResponse;
}


export interface CreateProjectRequest {
  spreadsheetId: string;
  confirmedNumber: number;
  metadata: ProjectMetadata;
  cityId?: number | null;
}


export interface CreateProjectResponse {
  projectId: string;
  projectNumber: number;
  projectName: string;
  driveFolderPending: boolean;
  driveFolderId: string | null;
  definitionsCount: number;
}


export interface CreateDriveFolderResponse {
  folderId: string;
  folderUrl: string;
  folderName: string;
}


export interface SuggestNumberResponse {
  suggested: number;
}
