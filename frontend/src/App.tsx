import { FormEvent, useEffect, useMemo, useState } from "react";
import { askQuestion, getDocuments } from "./api";
import type { AnswerPayload, DocumentView, EvidenceView, Mode, SessionEntry } from "./types";

const MODE_COPY: Record<Mode, { label: string; short: string; title: string; intro: string }> = {
  quick: {
    label: "Question rapide", short: "Deux assertions maximum",
    title: "Obtenir un chiffre prudentiel, avec sa preuve.",
    intro: "Une lecture courte pour vérifier une valeur et sa provenance sans masquer les champs manquants.",
  },
  deep: {
    label: "Analyse approfondie", short: "Contrat champ par champ",
    title: "Tester la complétude avant de synthétiser.",
    intro: "Le moteur planifie une requête par champ, fusionne les recherches et s’arrête sur contrat complet, conflit ou budget épuisé.",
  },
  summary: {
    label: "Synthèse structurée", short: "Brief sourcé et auditable",
    title: "Transformer plusieurs preuves en note structurée.",
    intro: "La rédaction reste subordonnée au gate : aucune conclusion ne peut inventer un champ absent du corpus.",
  },
};

const EXAMPLES: Record<Mode, Array<{ label: string; question: string; documentId: string; expected: string }>> = {
  quick: [
    { label: "Groupe Foyer", question: "Quel est le ratio de couverture SCR du Groupe Foyer en 2025 ?", documentId: "foyer_group_qrt_2025", expected: "3 champs QRT vérifiés" },
    { label: "Foyer Assurances", question: "Quel est le niveau de couverture SCR de Foyer Assurances en 2025 ?", documentId: "foyer_assurances_qrt_2025", expected: "Entité juridique détectée" },
    { label: "English query", question: "What is Foyer Global Health SCR coverage in 2025?", documentId: "foyer_global_health_qrt_2025", expected: "Bilingual mapping" },
  ],
  deep: [
    { label: "Contrat Groupe", question: "Quels éléments publics caractérisent la couverture prudentielle du Groupe Foyer en 2025 ?", documentId: "foyer_group_qrt_2025", expected: "Own funds + SCR + ratio" },
    { label: "Contrat entité", question: "Quels fonds propres éligibles, quel SCR et quel ratio Foyer Assurances publie-t-elle pour 2025 ?", documentId: "foyer_assurances_qrt_2025", expected: "3 preuves indépendantes" },
    { label: "Santé internationale", question: "Analyse la couverture prudentielle de Foyer Global Health en 2025.", documentId: "foyer_global_health_qrt_2025", expected: "Scope strict par entité" },
  ],
  summary: [
    { label: "Brief Groupe", question: "Présente une synthèse structurée de la couverture prudentielle du Groupe Foyer en 2025.", documentId: "foyer_group_qrt_2025", expected: "Synthèse sur preuves admises" },
    { label: "Brief Assurances", question: "Résume la position de solvabilité publiée par Foyer Assurances en 2025.", documentId: "foyer_assurances_qrt_2025", expected: "Restitution d’une entité" },
    { label: "Brief Global Health", question: "Summarise Foyer Global Health's published solvency position for 2025.", documentId: "foyer_global_health_qrt_2025", expected: "English input supported" },
  ],
};

function Icon({ name }: { name: "library" | "shield" | "spark" | "search" | "clock" | "external" | "home" | "plus" }) {
  const paths = {
    library: <path d="M4 5.5h16M6.5 3v16m5-16v16m5-16v16M4 19h16" />,
    shield: <path d="M12 3 4.8 6v5.2c0 4.5 3.1 7.4 7.2 9.8 4.1-2.4 7.2-5.3 7.2-9.8V6L12 3Zm-3 9 2 2 4-5" />,
    spark: <path d="m12 2 1.5 5.5L19 9l-5.5 1.5L12 16l-1.5-5.5L5 9l5.5-1.5L12 2Z" />,
    search: <path d="m20 20-4.5-4.5m2-5A7 7 0 1 1 3.5 10.5a7 7 0 0 1 14 0Z" />,
    clock: <path d="M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />,
    external: <path d="M14 4h6v6m0-6-9 9M10 6H5a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" />,
    home: <path d="m3 11 9-8 9 8M5 10v10h14V10M9 20v-6h6v6" />,
    plus: <path d="M12 5v14M5 12h14" />,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function loadSessions(): SessionEntry[] {
  const raw = localStorage.getItem("pel-conversations")
    ?? sessionStorage.getItem("pel-conversations")
    ?? localStorage.getItem("pel-sessions")
    ?? sessionStorage.getItem("pel-sessions");
  if (!raw) return [];
  try {
    type LegacySession = {
      id: string; createdAt: string; question: string; answer: AnswerPayload;
    };
    const parsed = JSON.parse(raw) as Array<SessionEntry | LegacySession>;
    return parsed.map((item): SessionEntry => {
      if ("turns" in item) return item;
      const documentIds: string[] = item.answer.evidence.flatMap((evidence) =>
        evidence.source?.document_id ? [evidence.source.document_id] : []
      );
      return {
        id: item.id, title: item.question, createdAt: item.createdAt,
        updatedAt: item.createdAt, mode: item.answer.mode,
        documentIds: [...new Set(documentIds)],
        turns: [{ id: item.id, createdAt: item.createdAt, question: item.question, answer: item.answer }],
        memory: compactMemory(item.answer),
      };
    });
  } catch { return []; }
}

function compactMemory(answer: AnswerPayload): string {
  const facts = answer.evidence
    .filter((item) => item.state === "ACCEPTED" && item.fact)
    .slice(0, 4)
    .map((item) => `${item.field_id}: ${item.fact?.formatted_value} [${item.fact?.entity}, ${item.fact?.period}]`);
  return `Validated profile: ${answer.profile_id}. Accepted facts: ${facts.join("; ") || "none"}. Missing fields: ${answer.missing_fields.join(", ") || "none"}.`.slice(0, 1200);
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentView[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [mode, setMode] = useState<Mode>("deep");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerPayload | null>(null);
  const [activeEvidenceId, setActiveEvidenceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [persistent, setPersistent] = useState(true);
  const [sessions, setSessions] = useState<SessionEntry[]>(loadSessions);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  useEffect(() => {
    getDocuments().then((list) => {
      setDocuments(list);
      setSelectedDocuments(list.filter((doc) => doc.status === "reviewed").map((doc) => doc.id));
    }).catch((caught: Error) => setError(caught.message));
  }, []);

  useEffect(() => {
    const target = persistent ? localStorage : sessionStorage;
    const other = persistent ? sessionStorage : localStorage;
    target.setItem("pel-conversations", JSON.stringify(sessions.slice(0, 12)));
    other.removeItem("pel-conversations");
  }, [sessions, persistent]);

  const activeSession = sessions.find((item) => item.id === activeSessionId) ?? null;
  const activeEvidence = useMemo(
    () => answer?.evidence.find((item) => item.id === activeEvidenceId) ?? answer?.evidence.find((item) => item.state === "ACCEPTED") ?? null,
    [answer, activeEvidenceId],
  );

  function goHome() {
    setActiveSessionId(null); setAnswer(null); setQuestion(""); setActiveEvidenceId(null); setError(null);
  }

  function useExample(example: (typeof EXAMPLES)[Mode][number]) {
    setSelectedDocuments([example.documentId]);
    setQuestion(example.question);
    setAnswer(null);
    setActiveSessionId(null);
  }

  function selectSession(session: SessionEntry) {
    const last = session.turns.at(-1);
    setActiveSessionId(session.id); setMode(session.mode); setSelectedDocuments(session.documentIds);
    setAnswer(last?.answer ?? null); setQuestion("");
    setActiveEvidenceId(last?.answer.evidence.find((item) => item.state === "ACCEPTED")?.id ?? null);
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3) return;
    setLoading(true); setError(null);
    try {
      const metadata = documents.filter((doc) => selectedDocuments.includes(doc.id));
      const entities = [...new Set(metadata.map((doc) => doc.entity))];
      const years = [...new Set(metadata.map((doc) => doc.year))];
      const payload = await askQuestion(trimmed, mode, selectedDocuments, {
        entity: metadata.length === 1 && entities.length === 1 ? entities[0] : undefined,
        period: metadata.length === 1 && years.length === 1 ? String(years[0]) : undefined,
      }, {
        profileId: activeSession?.turns.at(-1)?.answer.profile_id,
        conversationContext: activeSession?.memory,
      });
      const now = new Date().toISOString();
      const turn = { id: payload.request_id, createdAt: now, question: trimmed, answer: payload };
      const threadId = activeSession?.id ?? payload.request_id;
      setSessions((current) => {
        const existing = current.find((item) => item.id === threadId);
        const updated: SessionEntry = existing
          ? { ...existing, updatedAt: now, mode, documentIds: selectedDocuments, turns: [...existing.turns, turn], memory: compactMemory(payload) }
          : { id: threadId, title: trimmed, createdAt: now, updatedAt: now, mode, documentIds: selectedDocuments, turns: [turn], memory: compactMemory(payload) };
        return [updated, ...current.filter((item) => item.id !== threadId)].slice(0, 12);
      });
      setActiveSessionId(threadId); setAnswer(payload); setQuestion("");
      setActiveEvidenceId(payload.evidence.find((item) => item.state === "ACCEPTED" || item.state === "CONFLICT")?.id ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Une erreur inattendue est survenue.");
    } finally { setLoading(false); }
  }

  return <div className={`app-shell mode-${mode}`}>
    <header className="topbar">
      <button className="brand" onClick={goHome} aria-label="Retour à l’accueil"><span className="brand-mark"><Icon name="shield" /></span><span><small>AI ENGINEERING DEMONSTRATOR</small><strong>Prudential Evidence Lab</strong></span></button>
      <div className="topbar-actions"><span className="live-pill"><i />Corpus public contrôlé</span><button className="new-analysis" onClick={goHome}><Icon name="plus" /> Nouvelle analyse</button></div>
    </header>

    <main className="workspace">
      <aside className="sidebar library-panel">
        <div className="panel-heading"><span><Icon name="library" /> Bibliothèque</span><b>{selectedDocuments.length}/{documents.length}</b></div>
        <p>Six PDF publics : trois rapports narratifs et trois QRT tabulaires.</p>
        <div className="document-list">{documents.map((doc) => <label key={doc.id} className={`document-card ${selectedDocuments.includes(doc.id) ? "selected" : ""}`}>
          <input type="checkbox" checked={selectedDocuments.includes(doc.id)} onChange={() => setSelectedDocuments((current) => current.includes(doc.id) ? current.filter((id) => id !== doc.id) : [...current, doc.id])} />
          <span className="check" /><span><small>{doc.folder}</small><strong>{doc.title}</strong><em>{doc.year} · {doc.document_type}</em></span>
        </label>)}</div>
        <div className="history-title"><Icon name="clock" /> Analyses récentes</div>
        <label className="storage"><input type="checkbox" checked={persistent} onChange={(event) => setPersistent(event.target.checked)} /> Mémoriser sur cet appareil</label>
        <div className="session-list">{sessions.length === 0 && <small>Aucune analyse enregistrée.</small>}{sessions.map((session) => <button key={session.id} className={session.id === activeSessionId ? "active" : ""} onClick={() => selectSession(session)}><span>{session.title}</span><small>{session.turns.length} échange{session.turns.length > 1 ? "s" : ""} · {MODE_COPY[session.mode].label}</small></button>)}</div>
      </aside>

      <section className="conversation-panel">
        <nav className="mode-tabs" aria-label="Mode d’analyse">{(Object.keys(MODE_COPY) as Mode[]).map((item) => <button key={item} className={mode === item ? "active" : ""} onClick={() => { setMode(item); if (!activeSessionId) setAnswer(null); }}><strong>{MODE_COPY[item].label}</strong><small>{MODE_COPY[item].short}</small></button>)}</nav>
        <div className="conversation-scroll">
          {!answer && !loading && <Welcome mode={mode} onExample={useExample} />}
          {loading && <div className="loading-card"><span className="loader" /><div><strong>Construction du contrat de preuves</strong><small>Mapping · requêtes par champ · fusion hybride · validation</small></div></div>}
          {answer && !loading && <>
            <div className="thread-bar"><button onClick={goHome}><Icon name="home" /> Accueil</button><span>{activeSession?.turns.length ?? 1} échange{(activeSession?.turns.length ?? 1) > 1 ? "s" : ""} · mémoire factuelle active</span></div>
            {activeSession && activeSession.turns.length > 1 && <details className="thread-context"><summary>Contexte de la conversation ({activeSession.turns.length - 1} réponse antérieure)</summary>{activeSession.turns.slice(0, -1).map((turn) => <button key={turn.id} onClick={() => { setAnswer(turn.answer); setActiveEvidenceId(turn.answer.evidence.find((item) => item.state === "ACCEPTED")?.id ?? null); }}><strong>{turn.question}</strong><small>{turn.answer.status} · {turn.answer.profile_label}</small></button>)}</details>}
            <AnswerView answer={answer} onEvidence={setActiveEvidenceId} />
          </>}
          {error && <div className="error-banner">{error}</div>}
        </div>
        <form className="question-composer" onSubmit={submit}>
          <div className="scope-summary"><span>{selectedDocuments.length} document(s)</span><span>{activeSession ? "Continuer cette analyse" : MODE_COPY[mode].label}</span></div>
          <div className="composer-row"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={activeSession ? "Posez une question de suivi…" : "Posez une question sur le corpus sélectionné…"} rows={2} /><button disabled={loading || question.trim().length < 3 || !selectedDocuments.length}><Icon name="search" /><span>Analyser</span></button></div>
        </form>
      </section>

      <aside className="sidebar evidence-panel"><div className="panel-heading"><span><Icon name="shield" /> Transparence</span></div>{!answer ? <div className="empty-evidence"><Icon name="shield" /><strong>Aucune preuve sélectionnée</strong><span>Lancez une analyse puis inspectez chaque assertion.</span></div> : <EvidenceInspector answer={answer} evidence={activeEvidence} />}</aside>
    </main>
  </div>;
}

function Welcome({ mode, onExample }: { mode: Mode; onExample: (example: (typeof EXAMPLES)[Mode][number]) => void }) {
  const copy = MODE_COPY[mode];
  return <section className="welcome-card"><div className="welcome-kicker"><span><Icon name="spark" /></span>PARCOURS TESTÉ · {copy.label.toUpperCase()}</div><h2>{copy.title}</h2><p>{copy.intro}</p>
    <div className="process-strip"><span><b>01</b> Intention métier</span><span><b>02</b> Recherche multi-preuves</span><span><b>03</b> Gate de complétude</span></div>
    <div className="examples-heading"><strong>Scénarios prêts à démontrer</strong><small>Chaque carte sélectionne automatiquement le bon QRT public.</small></div>
    <div className="suggestions">{EXAMPLES[mode].map((example) => <button key={example.question} onClick={() => onExample(example)}><span>{example.label}</span><strong>{example.question}</strong><small>{example.expected} →</small></button>)}</div>
  </section>;
}

function AnswerView({ answer, onEvidence }: { answer: AnswerPayload; onEvidence: (id: string) => void }) {
  return <article className="answer-card"><header className="answer-header"><div><small>PROFIL DE PREUVES</small><h2>{answer.profile_label}</h2></div><b className={`answer-status ${answer.status.toLowerCase()}`}>{answer.status}</b></header><p className="answer-summary">{answer.summary}</p>
    <div className="coverage-grid">{answer.coverage.map((item) => <button key={item.field_id} className={`coverage-item ${item.state.toLowerCase()}`} disabled={!item.evidence_ids.length} onClick={() => item.evidence_ids[0] && onEvidence(item.evidence_ids[0])}><i>{item.state === "COVERED" ? "✓" : item.state === "CONFLICT" ? "!" : "—"}</i><span><strong>{item.label}</strong><small>{item.state === "COVERED" ? "Preuve acceptée" : item.state === "CONFLICT" ? "À examiner" : "Introuvable"}</small></span></button>)}</div>
    {!!answer.claims.length && <section className="claims-block"><h3>Assertions vérifiables</h3>{answer.claims.map((claim, index) => <button key={claim.id} onClick={() => claim.evidence_ids[0] && onEvidence(claim.evidence_ids[0])}><b>{String(index + 1).padStart(2, "0")}</b><span>{claim.text}</span><small>{claim.evidence_ids.length} source</small></button>)}</section>}
    <details className="trace-details"><summary>Piste d’audit de la récupération</summary><div><strong>Mapping · {answer.mapping_trace.decision_source}</strong><span>{answer.mapping_trace.profile_id} · confiance {answer.mapping_trace.confidence.toFixed(2)}</span><small>Entité {answer.mapping_trace.entity ?? "non contrainte"} · période {answer.mapping_trace.period ?? "non contrainte"}</small></div><div><strong>Récupération · {answer.retrieval_run.strategy}</strong><span>{answer.retrieval_run.dense_provider} · k={answer.retrieval_run.k_history.join("→")}</span><small>{answer.retrieval_run.rounds} tour(s) · arrêt {answer.retrieval_run.stop_reason}</small></div>{answer.query_trace.map((trace) => <div key={trace.field_id}><strong>{trace.field_id}</strong><span>{trace.query}</span><small>{trace.candidate_count} candidats · {trace.consulted_document_ids.length} documents</small></div>)}</details>
    <details className="trace-details"><summary>Appels modèles</summary>{answer.model_calls.map((call, index) => <div key={`${call.purpose}-${index}`}><strong>{call.provider} · {call.status}</strong><span>{call.model ?? "non configuré"}</span><small>{call.purpose} · {call.attempts} tentative(s) · {call.latency_ms} ms — {call.detail}</small></div>)}</details>
    <footer className="answer-footer"><span>{answer.latency_ms} ms</span><span>Synthèse {answer.generation_provider}</span><span>Corpus {answer.corpus_version}</span><span>ID {answer.request_id.slice(0, 8)}</span></footer>
  </article>;
}

function EvidenceInspector({ answer, evidence }: { answer: AnswerPayload; evidence: EvidenceView | null }) {
  if (!evidence) return <div className="empty-evidence"><strong>Aucune preuve admissible</strong><span>Les champs manquants restent visibles dans la réponse.</span></div>;
  return <div className="evidence-inspector"><div className="evidence-state-row"><b className={evidence.state.toLowerCase()}>{evidence.state}</b><small>{evidence.field_label}</small></div>
    {evidence.fact && <div className="fact-card"><small>VALEUR CONTRÔLÉE</small><strong>{evidence.fact.formatted_value}</strong><span>{evidence.fact.entity} · {evidence.fact.period}</span></div>}
    {evidence.excerpt && <blockquote>« {evidence.excerpt} »</blockquote>}
    {evidence.source && <div className="source-card"><small>SOURCE OFFICIELLE</small><strong>{evidence.source.document_title}</strong><dl><div><dt>Page</dt><dd>{evidence.source.page}</dd></div><div><dt>Section</dt><dd>{evidence.source.section_path.join(" › ")}</dd></div>{evidence.source.table_id && <div><dt>Table</dt><dd>{evidence.source.table_id}</dd></div>}</dl><a href={evidence.source.source_url} target="_blank" rel="noreferrer">Ouvrir le document <Icon name="external" /></a></div>}
    {evidence.score && <div className="score-card"><small>SCORES DE RÉCUPÉRATION</small><span>Lexical <b>#{evidence.score.lexical_rank}</b></span><span>Dense <b>#{evidence.score.dense_rank}</b></span><span>RRF <b>{evidence.score.rrf_score.toFixed(5)}</b></span></div>}
    <div className="reason-card"><small>DÉCISION DU GATE</small><p>{evidence.reason}</p></div><p className="corpus-note">La trace expose les preuves et les règles de décision, jamais une chaîne de pensée privée.</p><small>{answer.evidence.filter((item) => item.state === "ACCEPTED").length} preuve(s) acceptée(s)</small>
  </div>;
}
