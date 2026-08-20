import type { AnswerPayload, DocumentView, Mode, SuggestedQuestion } from "./types";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Erreur API (${response.status})`);
  return response.json() as Promise<T>;
}

export function getDocuments(): Promise<DocumentView[]> {
  return getJson("/api/documents");
}

export function getSuggestedQuestions(): Promise<SuggestedQuestion[]> {
  return getJson("/api/suggested-questions");
}

export async function askQuestion(
  question: string,
  mode: Mode,
  documentIds: string[],
): Promise<AnswerPayload> {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode, scope: { document_ids: documentIds } }),
  });
  if (!response.ok) {
    const message = response.status === 422 ? "La question n'est pas valide." : `Erreur API (${response.status})`;
    throw new Error(message);
  }
  return response.json() as Promise<AnswerPayload>;
}

