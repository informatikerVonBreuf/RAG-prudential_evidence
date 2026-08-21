import { FormEvent, useEffect, useMemo, useState } from "react";
import { askQuestion, getDocuments, getSuggestedQuestions } from "./api";
import type {
  AnswerPayload,
  DocumentView,
  EvidenceView,
  Mode,
  SessionEntry,
  SuggestedQuestion,
} from "./types";

const MODE_COPY: Record<Mode, { label: string; description: string }> = {
  quick: { label: "Question rapide", description: "Réponse ciblée, deux assertions maximum" },
  deep: { label: "Analyse approfondie", description: "Couverture champ par champ et manques visibles" },
  summary: { label: "Synthèse structurée", description: "Restitution ordonnée à partir des preuves" },
};

function Icon({ name }: { name: "library" | "shield" | "spark" | "search" | "clock" | "external" }) {
  const paths = {
    library: <path d="M4 5.5h16M6.5 3v16m5-16v16m5-16v16M4 19h16" />,
    shield: <path d="M12 3 4.8 6v5.2c0 4.5 3.1 7.4 7.2 9.8 4.1-2.4 7.2-5.3 7.2-9.8V6L12 3Zm-3 9 2 2 4-5" />,
    spark: <path d="m12 2 1.5 5.5L19 9l-5.5 1.5L12 16l-1.5-5.5L5 9l5.5-1.5L12 2Zm6 13 .7 2.3L21 18l-2.3.7L18 21l-.7-2.3L15 18l2.3-.7L18 15Z" />,
    search: <path d="m20 20-4.5-4.5m2-5A7 7 0 1 1 3.5 10.5a7 7 0 0 1 14 0Z" />,
    clock: <path d="M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />,
    external: <path d="M14 4h6v6m0-6-9 9M10 6H5a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" />,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function loadSessions(persistent: boolean): SessionEntry[] {
  const raw = (persistent ? localStorage : sessionStorage).getItem("pel-sessions");
  if (!raw) return [];
  try { return JSON.parse(raw) as SessionEntry[]; } catch { return []; }
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestedQuestion[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [mode, setMode] = useState<Mode>("deep");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerPayload | null>(null);
  const [activeEvidenceId, setActiveEvidenceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [persistent, setPersistent] = useState(false);
  const [sessions, setSessions] = useState<SessionEntry[]>(() => loadSessions(false));

  useEffect(() => {
    Promise.all([getDocuments(), getSuggestedQuestions()])
      .then(([documentList, questionList]) => {
        setDocuments(documentList);
        setSuggestions(questionList);
        setSelectedDocuments(documentList.filter((doc) => doc.status === "reviewed").map((doc) => doc.id));
      })
      .catch((caught: Error) => setError(caught.message));
  }, []);

  useEffect(() => {
    const target = persistent ? localStorage : sessionStorage;
    const other = persistent ? sessionStorage : localStorage;
    target.setItem("pel-sessions", JSON.stringify(sessions.slice(0, 12)));
    if (!persistent) other.removeItem("pel-sessions");
  }, [sessions, persistent]);

  const activeEvidence = useMemo(
    () => answer?.evidence.find((item) => item.id === activeEvidenceId) ?? answer?.evidence.find((item) => item.state === "ACCEPTED") ?? null,
    [answer, activeEvidenceId],
  );

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3) return;
    setLoading(true);
    setError(null);
    try {
      const selectedMetadata = documents.filter((doc) => selectedDocuments.includes(doc.id));
      const entities = [...new Set(selectedMetadata.map((doc) => doc.entity))];
      const years = [...new Set(selectedMetadata.map((doc) => doc.year))];
      const payload = await askQuestion(trimmed, mode, selectedDocuments, {
        entity: selectedMetadata.length === 1 && entities.length === 1 ? entities[0] : undefined,
        period: selectedMetadata.length === 1 && years.length === 1 ? String(years[0]) : undefined,
      });
      setAnswer(payload);
      const firstAccepted = payload.evidence.find((item) => item.state === "ACCEPTED" || item.state === "CONFLICT");
      setActiveEvidenceId(firstAccepted?.id ?? null);
      setSessions((current) => [
        { id: payload.request_id, createdAt: new Date().toISOString(), question: trimmed, answer: payload },
        ...current.filter((item) => item.id !== payload.request_id),
      ].slice(0, 12));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Une erreur inattendue est survenue.");
    } finally {
      setLoading(false);
    }
  }

  function toggleDocument(id: string) {
    setSelectedDocuments((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  function selectSession(session: SessionEntry) {
    setQuestion(session.question);
    setAnswer(session.answer);
    setActiveEvidenceId(session.answer.evidence.find((item) => item.state === "ACCEPTED")?.id ?? null);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark"><Icon name="shield" /></div>
        <div className="brand-copy">
          <div className="eyebrow">AI ENGINEERING DEMONSTRATOR</div>
          <h1>Prudential Evidence Lab</h1>
        </div>
        <div className="topbar-status"><span className="status-dot" /> Corpus public contrôlé</div>
      </header>

      <main className="workspace">
        <aside className="sidebar library-panel">
          <div className="panel-heading">
            <div><Icon name="library" /><span>Bibliothèque</span></div>
            <span className="count-badge">{selectedDocuments.length}/{documents.length}</span>
          </div>
          <p className="panel-intro">Sélectionnez le périmètre interrogé. Le corpus déployé est en lecture seule.</p>
          <div className="document-list">
            {documents.map((document) => (
              <label key={document.id} className={`document-card ${selectedDocuments.includes(document.id) ? "selected" : ""}`}>
                <input type="checkbox" checked={selectedDocuments.includes(document.id)} onChange={() => toggleDocument(document.id)} />
                <span className="checkbox-visual" />
                <span className="document-copy">
                  <span className="document-folder">{document.folder}</span>
                  <strong>{document.title}</strong>
                  <span className="document-meta"><span>{document.year}</span><span>{document.document_type}</span></span>
                  <span className={`document-status ${document.status}`}>{document.status === "synthetic" ? "Synthétique" : "Revu"}</span>
                </span>
              </label>
            ))}
          </div>

          <div className="history-header"><Icon name="clock" /><span>Historique</span></div>
          <label className="storage-toggle">
            <input type="checkbox" checked={persistent} onChange={(event) => setPersistent(event.target.checked)} />
            <span>Conserver dans ce navigateur</span>
          </label>
          <div className="session-list">
            {sessions.length === 0 && <span className="empty-history">Aucune question dans cette session.</span>}
            {sessions.slice(0, 5).map((session) => (
              <button key={session.id} onClick={() => selectSession(session)}>
                <span>{session.question}</span><small>{new Date(session.createdAt).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</small>
              </button>
            ))}
          </div>
        </aside>

        <section className="conversation-panel">
          <div className="mode-tabs" role="tablist" aria-label="Mode d'analyse">
            {(Object.keys(MODE_COPY) as Mode[]).map((item) => (
              <button key={item} role="tab" aria-selected={mode === item} className={mode === item ? "active" : ""} onClick={() => setMode(item)}>
                <span>{MODE_COPY[item].label}</span><small>{MODE_COPY[item].description}</small>
              </button>
            ))}
          </div>

          <div className="conversation-scroll">
            {!answer && !loading && (
              <div className="welcome-card">
                <div className="welcome-icon"><Icon name="spark" /></div>
                <span className="eyebrow">DE LA QUESTION À LA PREUVE</span>
                <h2>Interrogez les documents sans perdre la trace des affirmations.</h2>
                <p>Chaque question est transformée en champs obligatoires. Le code décide si les preuves suffisent ; l'interface expose ce qui manque.</p>
                <div className="suggestions">
                  {suggestions.map((suggestion) => (
                    <button key={suggestion.label} onClick={() => setQuestion(suggestion.question)}>
                      <span>{suggestion.label}</span><small>{suggestion.question}</small>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {loading && (
              <div className="loading-card">
                <div className="loader" />
                <div><strong>Construction du contrat de preuves</strong><span>Mapping · requêtes par champ · fusion RRF · validation</span></div>
              </div>
            )}

            {answer && !loading && (
              <AnswerView answer={answer} onEvidence={setActiveEvidenceId} />
            )}
            {error && <div className="error-banner">{error}</div>}
          </div>

          <form className="question-composer" onSubmit={submit}>
            <div className="scope-summary"><span>{selectedDocuments.length} document(s)</span><span>Mode : {MODE_COPY[mode].label}</span></div>
            <div className="composer-row">
              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Posez une question sur le corpus sélectionné…" rows={2} />
              <button type="submit" disabled={loading || question.trim().length < 3 || selectedDocuments.length === 0} aria-label="Lancer l'analyse">
                <Icon name="search" /><span>Analyser</span>
              </button>
            </div>
          </form>
        </section>

        <aside className="sidebar evidence-panel">
          <div className="panel-heading"><div><Icon name="shield" /><span>Transparence</span></div></div>
          {!answer && <div className="empty-evidence"><Icon name="shield" /><strong>Aucune preuve sélectionnée</strong><span>Lancez une analyse, puis cliquez sur une assertion pour inspecter sa provenance.</span></div>}
          {answer && <EvidenceInspector answer={answer} evidence={activeEvidence} />}
        </aside>
      </main>
    </div>
  );
}

function AnswerView({ answer, onEvidence }: { answer: AnswerPayload; onEvidence: (id: string) => void }) {
  return (
    <article className="answer-card">
      <div className="answer-header">
        <div><span className="eyebrow">PROFIL DE PREUVES</span><h2>{answer.profile_label}</h2></div>
        <span className={`answer-status ${answer.status.toLowerCase()}`}>{answer.status}</span>
      </div>
      <p className="answer-summary">{answer.summary}</p>

      <div className="coverage-grid">
        {answer.coverage.map((item) => (
          <button key={item.field_id} className={`coverage-item ${item.state.toLowerCase()}`} disabled={!item.evidence_ids.length} onClick={() => item.evidence_ids[0] && onEvidence(item.evidence_ids[0])}>
            <span className="coverage-icon">{item.state === "COVERED" ? "✓" : item.state === "CONFLICT" ? "!" : "—"}</span>
            <span><strong>{item.label}</strong><small>{item.state === "COVERED" ? "Preuve acceptée" : item.state === "CONFLICT" ? "À examiner" : "Introuvable"}</small></span>
          </button>
        ))}
      </div>

      {answer.claims.length > 0 && <div className="claims-block">
        <h3>Assertions vérifiables</h3>
        {answer.claims.map((claim, index) => (
          <button key={claim.id} className="claim-row" onClick={() => claim.evidence_ids[0] && onEvidence(claim.evidence_ids[0])}>
            <span className="claim-number">{String(index + 1).padStart(2, "0")}</span>
            <span>{claim.text}</span>
            <span className="citation-pill">{claim.evidence_ids.length} source</span>
          </button>
        ))}
      </div>}

      <details className="trace-details">
        <summary>Piste d'audit de la récupération</summary>
        {answer.query_trace.map((trace) => <div key={trace.field_id}><strong>{trace.field_id}</strong><span>{trace.query}</span><small>{trace.candidate_count} candidats · {trace.consulted_document_ids.length} documents</small></div>)}
      </details>
      <details className="trace-details">
        <summary>Appels modèles</summary>
        {answer.model_calls.map((call, index) => <div key={`${call.purpose}-${index}`}><strong>{call.provider} · {call.status}</strong><span>{call.model ?? "non configuré"}</span><small>{call.purpose} · {call.attempts} tentative(s) · {call.latency_ms} ms — {call.detail}</small></div>)}
      </details>
      <footer className="answer-footer"><span>{answer.latency_ms} ms</span><span>Synthèse {answer.generation_provider}</span><span>Corpus {answer.corpus_version}</span><span>ID {answer.request_id.slice(0, 8)}</span></footer>
    </article>
  );
}

function EvidenceInspector({ answer, evidence }: { answer: AnswerPayload; evidence: EvidenceView | null }) {
  if (!evidence) return <div className="empty-evidence"><strong>Aucune preuve admissible</strong><span>Consultez les champs manquants dans la réponse.</span></div>;
  return (
    <div className="evidence-inspector">
      <div className="evidence-state-row"><span className={`evidence-state ${evidence.state.toLowerCase()}`}>{evidence.state}</span><small>{evidence.field_label}</small></div>
      {evidence.fact && <div className="fact-card"><span>Valeur contrôlée</span><strong>{evidence.fact.formatted_value}</strong><div><span>{evidence.fact.entity}</span><span>{evidence.fact.period}</span></div></div>}
      {evidence.excerpt && <blockquote>« {evidence.excerpt} »</blockquote>}
      {evidence.source && <div className="source-card">
        <span className="section-label">SOURCE</span>
        <strong>{evidence.source.document_title}</strong>
        <dl>
          <div><dt>Version</dt><dd>{evidence.source.version}</dd></div>
          <div><dt>Page</dt><dd>{evidence.source.page}</dd></div>
          <div><dt>Section</dt><dd>{evidence.source.section_path.join(" › ")}</dd></div>
          {evidence.source.table_id && <><div><dt>Table</dt><dd>{evidence.source.table_id}</dd></div><div><dt>Cellule</dt><dd>{evidence.source.row} · {evidence.source.column}</dd></div></>}
        </dl>
        <a href={evidence.source.source_url} target="_blank" rel="noreferrer">Ouvrir la source officielle <Icon name="external" /></a>
      </div>}
      {evidence.score && <div className="score-card"><span className="section-label">TRACE DE SCORE</span><div><span>Rang lexical</span><strong>#{evidence.score.lexical_rank}</strong></div><div><span>Rang dense</span><strong>#{evidence.score.dense_rank}</strong></div><div><span>Score RRF</span><strong>{evidence.score.rrf_score.toFixed(5)}</strong></div></div>}
      <div className="reason-card"><span className="section-label">DÉCISION DU GATE</span><p>{evidence.reason}</p></div>
      <div className="corpus-note">La transparence expose les preuves et les règles de décision, pas une chaîne de pensée du modèle.</div>
      <div className="evidence-index">{answer.evidence.filter((item) => item.state === "ACCEPTED").length} preuve(s) acceptée(s) dans cette réponse</div>
    </div>
  );
}
