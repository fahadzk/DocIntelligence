import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { activityApi } from "../../services/api";
import type { ActivityEvent } from "../../types/activity";
import type { Project } from "../../types/projects";

const intervals = [0, 5, 10, 15, 30, 60];
function detail(value: unknown) { return typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? String(value) : JSON.stringify(value); }

export function ActivityWorkspace({ project, active = true }: { project: Project; active?: boolean }) {
  const saved = Number(localStorage.getItem("document-intelligence.activity-refresh") ?? "5");
  const [refreshSeconds, setRefreshSeconds] = useState(intervals.includes(saved) ? saved : 5);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const load = useCallback(async () => { try { setError(undefined); setEvents(await activityApi.list(project.id)); } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load activity."); } finally { setLoading(false); } }, [project.id]);
  useEffect(() => { if (!active) return; setLoading(true); void load(); }, [load, active]);
  useEffect(() => { localStorage.setItem("document-intelligence.activity-refresh", String(refreshSeconds)); if (!active || !refreshSeconds) return; const timer = window.setInterval(() => void load(), refreshSeconds * 1000); return () => window.clearInterval(timer); }, [refreshSeconds, load, active]);
  const status = useMemo(() => refreshSeconds ? `Refreshing every ${refreshSeconds} seconds` : "Automatic refresh is off", [refreshSeconds]);
  return <section className="activity-workspace">
    <div className="documents-heading"><div><p className="eyebrow">Project / Activity</p><h2>Processing activity</h2><p>Operational steps, timings, storage targets, and errors for this project. Document text and questions are not recorded.</p></div><Button variant="quiet" onClick={() => void load()}>Refresh now</Button></div>
    <div className="activity-controls"><label htmlFor="activity-refresh">Refresh</label><select id="activity-refresh" value={refreshSeconds} onChange={(event) => setRefreshSeconds(Number(event.target.value))}>{intervals.map((value) => <option key={value} value={value}>{value ? `${value} seconds` : "Disabled"}</option>)}</select><span>{status}</span></div>
    {loading ? <LoadingState label="Loading activity…" /> : error ? <ErrorState message={error} retry={() => void load()} /> : events.length === 0 ? <div className="search-empty">No recorded activity yet. Import a document, search, or ask a question to see the processing trail.</div> : <ol className="activity-list">{events.map((event) => <li key={event.id} className={`activity-event ${event.level === "error" ? "activity-error" : ""}`}><div className="activity-event-head"><div><strong>{event.message}</strong><span>{event.action}</span></div><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></div><div className="activity-details">{Object.entries(event.details).map(([key, value]) => <span key={key}><b>{key.replaceAll("_", " ")}:</b> {detail(value)}</span>)}{event.duration_ms !== null && <span><b>duration:</b> {event.duration_ms} ms</span>}</div></li>)}</ol>}
  </section>;
}