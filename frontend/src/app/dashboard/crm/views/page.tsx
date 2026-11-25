"use client";
// M43.S01.T016: sales teams (hierarchy), tags, saved views shown as list or calendar.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";
import { PipelineSelect } from "@/components/PipelineSelect";

interface Team { id: string; code: string; name: string; parent_id: string | null; members: { user_id: string; role: string }[] | null }
interface Tag { id: string; name: string }
interface View { id: string; name: string; view_type: string; filters: Record<string, string>; calendar_field: string | null; team_id: string | null }
interface Row { id: string; company_name: string; status: string; expected_revenue: number; currency: string; date: string | null }

const err = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : fb;
};

export default function CRMViewsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [views, setViews] = useState<View[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [team, setTeam] = useState({ code: "", name: "", parent_id: "" });
  const [member, setMember] = useState({ team_id: "", user_id: "" });
  const [tagName, setTagName] = useState("");
  const [draft, setDraft] = useState({ name: "", view_type: "list", pipeline_id: "", tag: "", status: "OPEN", team_id: "", calendar_field: "expected_close_date" });
  const [active, setActive] = useState<View | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const load = useCallback(() => {
    apiClient.get("/api/v1/crm-teams/teams").then((r) => setTeams(r.data)).catch(() => setTeams([]));
    apiClient.get("/api/v1/crm-teams/tags").then((r) => setTags(r.data)).catch(() => setTags([]));
    apiClient.get("/api/v1/crm-teams/views").then((r) => setViews(r.data)).catch(() => setViews([]));
  }, []);
  useEffect(() => { load(); }, [load]);
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); setMsg(ok); load(); } catch (e) { setMsg(err(e, "Not allowed.")); } };
  const open = async (v: View) => { setActive(v); try { setRows((await apiClient.get(`/api/v1/crm-teams/views/${v.id}/records`)).data); } catch { setRows([]); } };
  const tree = (parent: string | null, depth = 0): React.ReactNode[] => teams.filter((t) => t.parent_id === parent).flatMap((t) => [
    <div key={t.id} className="text-xs" style={{ paddingLeft: depth * 12 }}>{t.name} <span className="text-gray-400">({t.code}) · {t.members?.length ?? 0} people</span></div>,
    ...tree(t.id, depth + 1)]);

  return (
    <div className="p-4 grid lg:grid-cols-3 gap-4">
      {msg && <p role="status" className="lg:col-span-3 text-sm">{msg}</p>}
      <section className="border rounded bg-white p-3 space-y-2">
        <h3 className="text-sm font-semibold">Sales teams</h3>
        {tree(null)}
        <form className="space-y-1 text-xs" onSubmit={(e) => { e.preventDefault(); act(() => apiClient.post("/api/v1/crm-teams/teams", { ...team, parent_id: team.parent_id || null }), "Team added."); setTeam({ code: "", name: "", parent_id: "" }); }}>
          <div className="flex gap-1"><input required className="border rounded px-2 py-1 w-1/3" placeholder="Code" value={team.code} onChange={(e) => setTeam({ ...team, code: e.target.value })} />
            <input required className="border rounded px-2 py-1 flex-1" placeholder="Name" value={team.name} onChange={(e) => setTeam({ ...team, name: e.target.value })} /></div>
          <select className="border rounded px-2 py-1 w-full" value={team.parent_id} onChange={(e) => setTeam({ ...team, parent_id: e.target.value })}>
            <option value="">Top level</option>{teams.map((t) => <option key={t.id} value={t.id}>under {t.name}</option>)}</select>
          <button className="border rounded px-2 py-1">Add team</button>
        </form>
        <div className="space-y-1 text-xs">
          <select className="border rounded px-2 py-1 w-full" value={member.team_id} onChange={(e) => setMember({ ...member, team_id: e.target.value })}>
            <option value="">Team…</option>{teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>
          <EntityPicker kind="user" value={member.user_id} onChange={(id) => setMember({ ...member, user_id: id })} placeholder="Person…" />
          <button className="border rounded px-2 py-1" disabled={!member.team_id || !member.user_id}
                  onClick={() => act(() => apiClient.put(`/api/v1/crm-teams/teams/${member.team_id}/members`, { user_id: member.user_id }), "Member added.")}>Add member</button>
        </div>
      </section>
      <section className="border rounded bg-white p-3 space-y-2">
        <h3 className="text-sm font-semibold">Tags</h3>
        <div className="flex flex-wrap gap-1">{tags.map((t) => <span key={t.id} className="text-xs bg-gray-100 rounded px-2 py-0.5">{t.name}</span>)}</div>
        <form className="flex gap-1 text-xs" onSubmit={(e) => { e.preventDefault(); act(() => apiClient.post("/api/v1/crm-teams/tags", { name: tagName }), "Tag added."); setTagName(""); }}>
          <input required className="border rounded px-2 py-1 flex-1" placeholder="New tag" value={tagName} onChange={(e) => setTagName(e.target.value)} />
          <button className="border rounded px-2">Add</button></form>
        <h3 className="text-sm font-semibold pt-2">New saved view</h3>
        <form className="space-y-1 text-xs" onSubmit={(e) => {
          e.preventDefault();
          const filters: Record<string, string> = {};
          if (draft.pipeline_id) filters.pipeline_id = draft.pipeline_id;
          if (draft.tag) filters.tag = draft.tag;
          if (draft.status) filters.status = draft.status;
          act(() => apiClient.post("/api/v1/crm-teams/views", { name: draft.name, view_type: draft.view_type, filters, team_id: draft.team_id || null,
            calendar_field: draft.view_type === "calendar" ? draft.calendar_field : null }), "View saved.");
        }}>
          <input required className="border rounded px-2 py-1 w-full" placeholder="View name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          <PipelineSelect value={draft.pipeline_id} onChange={(id) => setDraft((d) => ({ ...d, pipeline_id: id }))} />
          <select className="border rounded px-2 py-1 w-full" value={draft.tag} onChange={(e) => setDraft({ ...draft, tag: e.target.value })}>
            <option value="">Any tag</option>{tags.map((t) => <option key={t.id}>{t.name}</option>)}</select>
          <select className="border rounded px-2 py-1 w-full" value={draft.view_type} onChange={(e) => setDraft({ ...draft, view_type: e.target.value })}>
            <option value="list">List</option><option value="calendar">Calendar</option></select>
          {draft.view_type === "calendar" && <select className="border rounded px-2 py-1 w-full" value={draft.calendar_field} onChange={(e) => setDraft({ ...draft, calendar_field: e.target.value })}>
            <option value="expected_close_date">by expected close date</option><option value="next_action_date">by next action date</option></select>}
          <select className="border rounded px-2 py-1 w-full" value={draft.team_id} onChange={(e) => setDraft({ ...draft, team_id: e.target.value })}>
            <option value="">Only me</option>{teams.map((t) => <option key={t.id} value={t.id}>Share with {t.name}</option>)}</select>
          <button className="bg-indigo-600 text-white rounded px-3 py-1">Save view</button>
        </form>
      </section>
      <section className="border rounded bg-white p-3 space-y-2">
        <h3 className="text-sm font-semibold">My views</h3>
        <div className="flex flex-wrap gap-1">{views.map((v) => (
          <button key={v.id} className={`text-xs border rounded px-2 py-1 ${active?.id === v.id ? "bg-indigo-600 text-white" : ""}`} onClick={() => open(v)}>{v.name}{v.team_id ? " (team)" : ""}</button>))}</div>
        {active && (active.view_type === "calendar" ? <Calendar rows={rows} /> : (
          <ul className="text-xs divide-y">{rows.map((r) => <li key={r.id} className="py-1 flex justify-between gap-2"><span>{r.company_name}</span><span className="text-gray-500">{r.currency} {r.expected_revenue.toLocaleString()} · {r.status}</span></li>)}
            {rows.length === 0 && <li className="text-gray-500 py-1">No matching records.</li>}</ul>))}
      </section>
    </div>
  );
}

function Calendar({ rows }: { rows: Row[] }) {
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const days = useMemo(() => {
    const first = (month.getDay() + 6) % 7;
    const n = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    return [...Array(first).fill(null), ...Array.from({ length: n }, (_, i) => i + 1)];
  }, [month]);
  const key = (d: number) => `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  return (
    <div className="text-xs">
      <div className="flex justify-between items-center mb-1">
        <button aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>‹</button>
        <span>{month.toLocaleDateString([], { month: "long", year: "numeric" })}</span>
        <button aria-label="Next month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>›</button>
      </div>
      <div className="grid grid-cols-7 gap-px bg-gray-200">
        {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((d) => <div key={d} className="bg-gray-50 text-center">{d}</div>)}
        {days.map((d, i) => (
          <div key={i} className="bg-white min-h-[3rem] p-0.5">
            {d && <><div className="text-gray-400">{d}</div>
              {rows.filter((r) => r.date === key(d)).map((r) => <div key={r.id} className="truncate bg-indigo-50 rounded px-0.5" title={r.company_name}>{r.company_name}</div>)}</>}
          </div>
        ))}
      </div>
    </div>
  );
}
