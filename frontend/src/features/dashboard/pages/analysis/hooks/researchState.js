export const isResearchActive = (run) => ["PENDING", "RUNNING"].includes(run?.status);

export function mergeResearchRuns(previous, incoming, full = true) {
  const records = new Map(previous.map((run) => [run.id, run]));
  for (const run of incoming) {
    const current = records.get(run.id);
    if (current && current.revision > run.revision) continue;
    records.set(run.id, { ...current, ...run, ...(full ? { loadedRevision: run.revision } : {}) });
  }
  return [...records.values()].sort((a, b) => a.id - b.id);
}
