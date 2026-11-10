"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qmsApi, CalibrationRecord } from "@/lib/qms";
import { maintenanceApi } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PermissionGuard, RequirePermission } from "@/components/PermissionGuard";

type InstrumentForm = {
  instrument_id: string;
  instrument_name: string;
  instrument_type: string;
  asset_id: string;
  location: string;
  manufacturer: string;
  model_no: string;
  serial_no: string;
  calibration_interval_days: string;
  notes: string;
};

const emptyForm: InstrumentForm = {
  instrument_id: "", instrument_name: "", instrument_type: "", asset_id: "", location: "",
  manufacturer: "", model_no: "", serial_no: "", calibration_interval_days: "365", notes: "",
};

const statusVariant = (status: string) =>
  status === "CURRENT" ? "green" : status === "OVERDUE" ? "red" : status === "DUE_SOON" ? "yellow" : "gray";

export default function CalibrationRegistryPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState<InstrumentForm>(emptyForm);
  const [editing, setEditing] = useState<CalibrationRecord | null>(null);
  const [open, setOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [dueFrom, setDueFrom] = useState("");
  const [dueTo, setDueTo] = useState("");
  const [historyInstrument, setHistoryInstrument] = useState<CalibrationRecord | null>(null);
  const [historyForm, setHistoryForm] = useState({
    calibration_date: "", calibration_authority: "", certificate_ref: "", result: "", notes: "",
  });
  const [historyError, setHistoryError] = useState("");

  const instrumentsQuery = useQuery({
    queryKey: ["qms-calibration-instruments", statusFilter],
    queryFn: () => qmsApi.listCalibrations(statusFilter || undefined),
  });
  const scheduleQuery = useQuery({
    queryKey: ["qms-calibration-schedule", dueFrom, dueTo],
    queryFn: () => qmsApi.getCalibrationSchedule(dueFrom || undefined, dueTo || undefined),
  });
  const assetsQuery = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
    enabled: open,
  });
  const historyQuery = useQuery({
    queryKey: ["qms-calibration-history", historyInstrument?.id],
    queryFn: () => qmsApi.getCalibrationHistory(historyInstrument!.id),
    enabled: Boolean(historyInstrument),
  });

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        instrument_name: form.instrument_name.trim(),
        instrument_type: form.instrument_type.trim(),
        asset_id: form.asset_id || null,
        location: form.location || null,
        manufacturer: form.manufacturer || null,
        model_no: form.model_no || null,
        serial_no: form.serial_no || null,
        calibration_interval_days: Number(form.calibration_interval_days),
        notes: form.notes || null,
      };
      return editing
        ? qmsApi.updateCalibration(editing.id, payload)
        : qmsApi.createCalibration({ ...payload, instrument_id: form.instrument_id.trim() });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["qms-calibration-instruments"] });
      qc.invalidateQueries({ queryKey: ["qms-calibration-schedule"] });
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
    },
  });

  const historySave = useMutation({
    mutationFn: () => {
      if (!historyInstrument) throw new Error("Select an instrument first");
      return qmsApi.recordCalibrationEvent(historyInstrument.id, historyForm);
    },
    onSuccess: async () => {
      setHistoryError("");
      setHistoryForm({ calibration_date: "", calibration_authority: "", certificate_ref: "", result: "", notes: "" });
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["qms-calibration-history", historyInstrument?.id] }),
        qc.invalidateQueries({ queryKey: ["qms-calibration-instruments"] }),
        qc.invalidateQueries({ queryKey: ["qms-calibration-schedule"] }),
      ]);
    },
    onError: () => setHistoryError("The calibration event was not saved. Check the date, certificate reference, and permissions."),
  });

  const openCreate = () => { setEditing(null); setForm(emptyForm); setOpen(true); };
  const openHistory = (instrument: CalibrationRecord) => {
    setHistoryInstrument(instrument);
    setHistoryError("");
    setHistoryForm({ calibration_date: "", calibration_authority: "", certificate_ref: "", result: "", notes: "" });
  };
  const openEdit = (instrument: CalibrationRecord) => {
    setEditing(instrument);
    setForm({
      instrument_id: instrument.instrument_id,
      instrument_name: instrument.instrument_name,
      instrument_type: instrument.instrument_type,
      asset_id: instrument.asset_id ?? "",
      location: instrument.location ?? "",
      manufacturer: instrument.manufacturer ?? "",
      model_no: instrument.model_no ?? "",
      serial_no: instrument.serial_no ?? "",
      calibration_interval_days: String(instrument.calibration_interval_days),
      notes: instrument.notes ?? "",
    });
    setOpen(true);
  };

  const updateField = (field: keyof InstrumentForm, value: string) => setForm((current) => ({ ...current, [field]: value }));
  const valid = form.instrument_name.trim().length > 0
    && form.instrument_type.trim().length > 0
    && Number.isInteger(Number(form.calibration_interval_days))
    && Number(form.calibration_interval_days) > 0;

  return (
    <RequirePermission permission="quality.view">
      <div className="space-y-6 p-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Calibration instrument registry</h1>
            <p className="mt-1 text-sm text-gray-500">Register instruments and optionally link each one to a maintenance asset. Due status is derived from recorded dates; no facility instruments are preloaded.</p>
          </div>
          <PermissionGuard permission="quality.create">
            <Button onClick={openCreate}>Register instrument</Button>
          </PermissionGuard>
        </header>

        <section className="space-y-3 rounded-lg border bg-white p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><h2 className="font-semibold text-gray-900">Calibration schedule</h2><p className="text-xs text-gray-500">Read-only due window; it does not create appointments or calibration events.</p></div>
            <div className="flex flex-wrap gap-2">
              <label className="text-xs text-gray-600">Due from<input type="date" className="mt-1 block rounded border px-2 py-1.5" value={dueFrom} onChange={(event) => setDueFrom(event.target.value)} /></label>
              <label className="text-xs text-gray-600">Due through<input type="date" className="mt-1 block rounded border px-2 py-1.5" value={dueTo} onChange={(event) => setDueTo(event.target.value)} /></label>
            </div>
          </div>
          {scheduleQuery.isError ? <p className="text-sm text-red-700">The schedule status could not be loaded.</p> : null}
          {scheduleQuery.data ? (
            <>
              <p className="text-xs text-gray-500">As of {scheduleQuery.data.as_of}; due window {scheduleQuery.data.due_from} through {scheduleQuery.data.due_to}.</p>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="rounded bg-blue-50 p-3"><p className="text-xs text-blue-800">Due in window</p><p className="text-xl font-semibold text-blue-900">{scheduleQuery.data.due_in_range.length}</p></div>
                <div className="rounded bg-red-50 p-3"><p className="text-xs text-red-800">Overdue</p><p className="text-xl font-semibold text-red-900">{scheduleQuery.data.overdue.length}</p></div>
                <div className="rounded bg-amber-50 p-3"><p className="text-xs text-amber-800">Not verified</p><p className="text-xl font-semibold text-amber-900">{scheduleQuery.data.not_verified.length}</p></div>
                <div className="rounded bg-gray-50 p-3"><p className="text-xs text-gray-700">Out of service</p><p className="text-xl font-semibold text-gray-900">{scheduleQuery.data.out_of_service_count}</p></div>
              </div>
              {[...scheduleQuery.data.overdue, ...scheduleQuery.data.due_in_range].length > 0 ? (
                <div className="overflow-x-auto rounded border">
                  <table className="w-full text-sm"><thead><tr className="bg-gray-50 text-left text-xs uppercase text-gray-500"><th className="px-3 py-2">Instrument</th><th className="px-3 py-2">Asset</th><th className="px-3 py-2">Next due</th><th className="px-3 py-2">Days</th><th className="px-3 py-2">Status</th></tr></thead>
                    <tbody className="divide-y">{[...scheduleQuery.data.overdue, ...scheduleQuery.data.due_in_range].map((instrument) => (
                      <tr key={instrument.id}><td className="px-3 py-2">{instrument.instrument_id} — {instrument.instrument_name}</td><td className="px-3 py-2">{instrument.asset_no || "Unlinked"}</td><td className="px-3 py-2">{instrument.next_calibration_due || "—"}</td><td className="px-3 py-2">{instrument.days_until_due ?? "—"}</td><td className="px-3 py-2"><Badge label={instrument.status.replaceAll("_", " ")} variant={statusVariant(instrument.status)} /></td></tr>
                    ))}</tbody>
                  </table>
                </div>
              ) : <p className="text-sm text-gray-500">No active instruments are due in this window or overdue.</p>}
              {scheduleQuery.data.data_notes.map((note) => <p key={note} className="text-xs text-gray-500">{note}</p>)}
            </>
          ) : null}
        </section>

        {instrumentsQuery.isError ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">The instrument registry could not be loaded. Check QMS access and retry.</p> : null}
        <div className="flex items-end justify-between gap-3">
          <h2 className="font-semibold text-gray-900">Instrument register</h2>
          <label className="text-xs text-gray-600">Status filter<select className="ml-2 rounded border px-2 py-1.5 text-sm" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">All</option><option value="CURRENT">Current</option><option value="DUE_SOON">Due soon</option><option value="OVERDUE">Overdue</option><option value="NOT_VERIFIED">Not verified</option><option value="OUT_OF_SERVICE">Out of service</option>
          </select></label>
        </div>
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full text-sm">
            <thead><tr className="border-b bg-gray-50 text-left text-xs uppercase text-gray-500">
              <th className="px-4 py-3">Instrument ID</th><th className="px-4 py-3">Name / Type</th><th className="px-4 py-3">Linked asset</th><th className="px-4 py-3">Location / Serial</th><th className="px-4 py-3">Last / Next due</th><th className="px-4 py-3">Calibration status</th><th className="px-4 py-3">Active</th><th className="px-4 py-3" />
            </tr></thead>
            <tbody className="divide-y">
              {(instrumentsQuery.data ?? []).map((instrument) => (
                <tr key={instrument.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{instrument.instrument_id}</td>
                  <td className="px-4 py-3"><div className="font-medium">{instrument.instrument_name}</div><div className="text-xs text-gray-500">{instrument.instrument_type}</div></td>
                  <td className="px-4 py-3">{instrument.asset_no ? <><div>{instrument.asset_no}</div><div className="text-xs text-gray-500">{instrument.asset_name}</div></> : <span className="text-gray-400">Unlinked</span>}</td>
                  <td className="px-4 py-3 text-gray-600">{instrument.location || "—"}<div className="text-xs text-gray-500">{instrument.serial_no || "No serial recorded"}</div></td>
                  <td className="px-4 py-3 text-xs text-gray-600">Last: {instrument.last_calibration_date || "not recorded"}<div>Next: {instrument.next_calibration_due || "not scheduled"}</div></td>
                  <td className="px-4 py-3"><Badge label={instrument.status.replaceAll("_", " ")} variant={statusVariant(instrument.status)} /></td>
                  <td className="px-4 py-3">{instrument.is_active ? "Yes" : "No"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <PermissionGuard permission="quality.view"><Button variant="secondary" onClick={() => openHistory(instrument)}>History</Button></PermissionGuard>
                      <PermissionGuard permission="quality.edit"><Button variant="secondary" onClick={() => openEdit(instrument)}>Edit</Button></PermissionGuard>
                    </div>
                  </td>
                </tr>
              ))}
              {!instrumentsQuery.isLoading && (instrumentsQuery.data?.length ?? 0) === 0 ? <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-400">No instruments registered</td></tr> : null}
              {instrumentsQuery.isLoading ? <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-500">Loading instruments…</td></tr> : null}
            </tbody>
          </table>
        </div>

        {open ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="max-h-[90vh] w-full max-w-2xl space-y-4 overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
              <div><h2 className="text-lg font-semibold">{editing ? "Edit instrument" : "Register instrument"}</h2><p className="text-xs text-gray-500">No calibration event or certificate is created by registering an instrument.</p></div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="text-xs text-gray-600">Instrument ID<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.instrument_id} disabled={Boolean(editing)} onChange={(event) => updateField("instrument_id", event.target.value)} /></label>
                <label className="text-xs text-gray-600">Instrument name<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.instrument_name} onChange={(event) => updateField("instrument_name", event.target.value)} /></label>
                <label className="text-xs text-gray-600">Instrument type<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.instrument_type} onChange={(event) => updateField("instrument_type", event.target.value)} placeholder="e.g. digital scale" /></label>
                <label className="text-xs text-gray-600">Maintenance asset (optional)
                  <select className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.asset_id} onChange={(event) => updateField("asset_id", event.target.value)}>
                    <option value="">No linked asset</option>{(assetsQuery.data ?? []).map((asset) => <option key={asset.id} value={asset.id}>{asset.asset_no} — {asset.name}</option>)}
                  </select>
                </label>
                {assetsQuery.isError ? <p className="text-xs text-amber-700 md:col-span-2">Maintenance asset choices are unavailable; the instrument can still be registered without a link.</p> : null}
                <label className="text-xs text-gray-600">Location<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.location} onChange={(event) => updateField("location", event.target.value)} /></label>
                <label className="text-xs text-gray-600">Manufacturer<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.manufacturer} onChange={(event) => updateField("manufacturer", event.target.value)} /></label>
                <label className="text-xs text-gray-600">Model<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.model_no} onChange={(event) => updateField("model_no", event.target.value)} /></label>
                <label className="text-xs text-gray-600">Serial number<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.serial_no} onChange={(event) => updateField("serial_no", event.target.value)} /></label>
                <label className="text-xs text-gray-600">Calibration interval (days)<input type="number" min="1" max="36500" className="mt-1 w-full rounded border px-3 py-2 text-sm" value={form.calibration_interval_days} onChange={(event) => updateField("calibration_interval_days", event.target.value)} /></label>
                <label className="text-xs text-gray-600 md:col-span-2">Notes<textarea className="mt-1 w-full rounded border px-3 py-2 text-sm" rows={3} value={form.notes} onChange={(event) => updateField("notes", event.target.value)} /></label>
              </div>
              <p className="text-xs text-gray-500">Without a recorded calibration date, status is NOT VERIFIED; this means the record is missing evidence and does not claim the instrument was never calibrated. The existing software default interval is 365 days and can be changed.</p>
              {save.isError ? <p className="text-sm text-red-700">Could not save. Check required fields, duplicate IDs, and your QMS permissions.</p> : null}
              <div className="flex justify-end gap-2"><Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button loading={save.isPending} disabled={!valid || (!editing && !form.instrument_id.trim())} onClick={() => save.mutate()}>{editing ? "Save changes" : "Register"}</Button></div>
            </div>
          </div>
        ) : null}
        {historyInstrument ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="max-h-[90vh] w-full max-w-3xl space-y-4 overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Calibration history — {historyInstrument.instrument_id}</h2>
                  <p className="text-xs text-gray-500">Enter the actual certificate reference and outcome. This stores metadata only; it does not upload or generate a certificate file.</p>
                </div>
                <Button variant="secondary" onClick={() => setHistoryInstrument(null)}>Close</Button>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <label className="text-xs text-gray-600">Calibration date<input type="date" className="mt-1 w-full rounded border px-3 py-2 text-sm" value={historyForm.calibration_date} onChange={(event) => setHistoryForm((current) => ({ ...current, calibration_date: event.target.value }))} /></label>
                <label className="text-xs text-gray-600">Calibration authority<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={historyForm.calibration_authority} onChange={(event) => setHistoryForm((current) => ({ ...current, calibration_authority: event.target.value }))} /></label>
                <label className="text-xs text-gray-600">Certificate/report reference<input className="mt-1 w-full rounded border px-3 py-2 text-sm" value={historyForm.certificate_ref} onChange={(event) => setHistoryForm((current) => ({ ...current, certificate_ref: event.target.value }))} /></label>
                <label className="text-xs text-gray-600">Recorded outcome<select className="mt-1 w-full rounded border px-3 py-2 text-sm" value={historyForm.result} onChange={(event) => setHistoryForm((current) => ({ ...current, result: event.target.value }))}><option value="">Select actual outcome</option><option value="PASS">Pass</option><option value="FAIL">Fail</option></select></label>
                <label className="text-xs text-gray-600 md:col-span-2">Notes<textarea className="mt-1 w-full rounded border px-3 py-2 text-sm" rows={2} value={historyForm.notes} onChange={(event) => setHistoryForm((current) => ({ ...current, notes: event.target.value }))} /></label>
              </div>
              {historyError ? <p role="alert" className="text-sm text-red-700">{historyError}</p> : null}
              <div className="flex justify-end">
                <Button loading={historySave.isPending} disabled={!historyForm.calibration_date || !historyForm.calibration_authority.trim() || !historyForm.certificate_ref.trim() || !historyForm.result} onClick={() => historySave.mutate()}>Record calibration event</Button>
              </div>
              <section className="space-y-2 border-t pt-4">
                <h3 className="font-semibold">Recorded events</h3>
                {historyQuery.isLoading ? <p className="text-sm text-gray-500">Loading history…</p> : null}
                {historyQuery.isError ? <p className="text-sm text-red-700">Calibration history could not be loaded.</p> : null}
                {(historyQuery.data ?? []).map((event) => (
                  <article key={event.id} className="rounded border p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <strong>{event.calibration_date} · {event.result}</strong>
                      <span className="text-gray-500">Next due {event.next_calibration_due} · {event.calibration_interval_days} days</span>
                    </div>
                    <p className="mt-1 text-gray-700">{event.calibration_authority} · Ref: {event.certificate_ref}</p>
                    {event.notes ? <p className="mt-1 text-xs text-gray-500">{event.notes}</p> : null}
                  </article>
                ))}
                {!historyQuery.isLoading && !historyQuery.isError && (historyQuery.data?.length ?? 0) === 0 ? <p className="text-sm text-gray-500">No calibration events recorded.</p> : null}
              </section>
            </div>
          </div>
        ) : null}
      </div>
    </RequirePermission>
  );
}
