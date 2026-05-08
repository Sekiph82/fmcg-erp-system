"use client";
import { useEffect, useState } from "react";
import { qmsApi, CalibrationRecord } from "@/lib/qms";

const STATUS_COLORS: Record<string, string> = {
  CURRENT: "bg-green-100 text-green-700",
  DUE_SOON: "bg-amber-100 text-amber-700",
  OVERDUE: "bg-red-100 text-red-600",
  OUT_OF_SERVICE: "bg-gray-100 text-gray-500",
};

const BLANK = {
  instrument_id: "", instrument_name: "", instrument_type: "",
  location: "", serial_no: "", manufacturer: "", model_no: "",
  last_calibration_date: "", calibration_interval_days: "365",
  calibration_authority: "", certificate_ref: "", notes: "",
};

export default function CalibrationPage() {
  const [instruments, setInstruments] = useState<CalibrationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [recalModal, setRecalModal] = useState<CalibrationRecord | null>(null);
  const [recalDate, setRecalDate] = useState("");
  const [recalCert, setRecalCert] = useState("");
  const [form, setForm] = useState({ ...BLANK });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await qmsApi.listCalibrations(filterStatus || undefined);
      setInstruments(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus]);

  const create = async () => {
    if (!form.instrument_id || !form.instrument_name || !form.instrument_type) {
      setError("Instrument ID, Name, Type required"); return;
    }
    setSaving(true); setError("");
    try {
      await qmsApi.createCalibration({
        instrument_id: form.instrument_id,
        instrument_name: form.instrument_name,
        instrument_type: form.instrument_type,
        location: form.location || null,
        serial_no: form.serial_no || null,
        manufacturer: form.manufacturer || null,
        model_no: form.model_no || null,
        last_calibration_date: form.last_calibration_date || null,
        calibration_interval_days: parseInt(form.calibration_interval_days) || 365,
        calibration_authority: form.calibration_authority || null,
        certificate_ref: form.certificate_ref || null,
        notes: form.notes || null,
      });
      setShowCreate(false);
      setForm({ ...BLANK });
      await load();
    } catch {
      setError("Failed to create");
    } finally {
      setSaving(false);
    }
  };

  const recalibrate = async () => {
    if (!recalModal || !recalDate) { setError("Date required"); return; }
    setSaving(true); setError("");
    try {
      await qmsApi.updateCalibration(recalModal.id, {
        last_calibration_date: recalDate,
        certificate_ref: recalCert || null,
      });
      setRecalModal(null);
      setRecalDate("");
      setRecalCert("");
      await load();
    } catch {
      setError("Failed to update");
    } finally {
      setSaving(false);
    }
  };

  const overdue = instruments.filter(i => i.is_overdue).length;
  const dueSoon = instruments.filter(i => i.status === "DUE_SOON").length;
  const current = instruments.filter(i => i.status === "CURRENT").length;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Instrument Calibration</h1>
          <p className="text-xs text-gray-500 mt-0.5">Track calibration status, due dates, and certificates for all lab instruments.</p>
        </div>
        <button onClick={() => { setShowCreate(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Add Instrument
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Overdue", value: overdue, color: "text-red-600" },
          { label: "Due Soon", value: dueSoon, color: "text-amber-600" },
          { label: "Current", value: current, color: "text-green-600" },
        ].map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm text-center">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{loading ? "—" : s.value}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {["", "OVERDUE", "DUE_SOON", "CURRENT", "OUT_OF_SERVICE"].map(s => (
          <button key={s}
            onClick={() => setFilterStatus(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              filterStatus === s
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"
            }`}>
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : instruments.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">🔬</p>
          <p className="text-sm">No instruments registered.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["ID", "Name", "Type", "Location", "Last Cal.", "Next Due", "Days", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {instruments.map(inst => (
                <tr key={inst.id} className={`hover:bg-gray-50 ${!inst.is_active ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{inst.instrument_id}</td>
                  <td className="px-4 py-3 font-medium text-gray-800 text-sm">{inst.instrument_name}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{inst.instrument_type}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{inst.location ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{inst.last_calibration_date ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{inst.next_calibration_due ?? "—"}</td>
                  <td className="px-4 py-3 text-xs">
                    {inst.days_until_due != null ? (
                      <span className={inst.is_overdue ? "text-red-600 font-semibold" : inst.days_until_due <= 30 ? "text-amber-600" : "text-green-600"}>
                        {inst.is_overdue ? `${Math.abs(inst.days_until_due)}d over` : `${inst.days_until_due}d`}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[inst.status] ?? "bg-gray-100 text-gray-500"}`}>
                      {inst.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => { setRecalModal(inst); setRecalDate(""); setRecalCert(""); setError(""); }}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Recalibrate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Register Instrument</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Instrument ID *", key: "instrument_id", placeholder: "LAB-PH-001", col: 1 },
                  { label: "Instrument Name *", key: "instrument_name", placeholder: "pH Meter", col: 1 },
                  { label: "Type *", key: "instrument_type", placeholder: "pH Meter", col: 1 },
                  { label: "Location", key: "location", placeholder: "QC Lab", col: 1 },
                  { label: "Manufacturer", key: "manufacturer", placeholder: "", col: 1 },
                  { label: "Model No.", key: "model_no", placeholder: "", col: 1 },
                  { label: "Serial No.", key: "serial_no", placeholder: "", col: 1 },
                  { label: "Last Calibration Date", key: "last_calibration_date", type: "date", col: 1 },
                  { label: "Calibration Interval (days)", key: "calibration_interval_days", type: "number", placeholder: "365", col: 1 },
                  { label: "Calibration Authority", key: "calibration_authority", placeholder: "KEBS", col: 1 },
                  { label: "Certificate Ref", key: "certificate_ref", placeholder: "", col: 2 },
                  { label: "Notes", key: "notes", placeholder: "", col: 2 },
                ].map(f => (
                  <div key={f.key} className={f.col === 2 ? "col-span-2" : ""}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
                    <input type={f.type ?? "text"} placeholder={f.placeholder}
                      value={(form as Record<string, string>)[f.key]}
                      onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                ))}
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={create} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Saving…" : "Register"}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Recalibrate Modal */}
      {recalModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm">
            <div className="px-6 py-4 border-b">
              <h2 className="text-base font-semibold">Record Calibration</h2>
              <p className="text-xs text-gray-500 mt-0.5">{recalModal.instrument_name}</p>
            </div>
            <div className="p-6 space-y-4">
              {error && <p className="text-xs text-red-500">{error}</p>}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Calibration Date *</label>
                <input type="date" value={recalDate} onChange={e => setRecalDate(e.target.value)}
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Certificate Reference</label>
                <input type="text" value={recalCert} onChange={e => setRecalCert(e.target.value)}
                  placeholder="e.g. KEBS-2026-001"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={recalibrate} disabled={saving}
                className="flex-1 rounded bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
                {saving ? "Saving…" : "Record Calibration"}
              </button>
              <button onClick={() => setRecalModal(null)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
