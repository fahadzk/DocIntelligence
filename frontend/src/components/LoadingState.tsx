export function LoadingState({ label = "Loading workspace…" }: { label?: string }) { return <div className="loading-state" role="status"><span className="spinner" />{label}</div>; }
