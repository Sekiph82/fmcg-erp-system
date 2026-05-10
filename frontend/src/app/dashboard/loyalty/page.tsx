"use client";
import { useCallback, useEffect, useState } from "react";
import { loyaltyApi, LoyaltyAccount, LoyaltyTier, LoyaltyStats, TXN_COLORS, LoyaltyAccountDetail } from "@/lib/loyalty";

export default function LoyaltyPage() {
  const [stats, setStats] = useState<LoyaltyStats | null>(null);
  const [tiers, setTiers] = useState<LoyaltyTier[]>([]);
  const [accounts, setAccounts] = useState<LoyaltyAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState<LoyaltyAccountDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filterTier, setFilterTier] = useState("");

  // Modals
  const [showEnroll, setShowEnroll] = useState(false);
  const [showEarn, setShowEarn] = useState(false);
  const [showRedeem, setShowRedeem] = useState(false);
  const [enrollForm, setEnrollForm] = useState({ customer_id: "", initial_points: "0" });
  const [earnForm, setEarnForm] = useState({ points: "", spend_amount: "", description: "" });
  const [redeemForm, setRedeemForm] = useState({ points: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, t, a] = await Promise.all([
        loyaltyApi.getStats(),
        loyaltyApi.listTiers(),
        loyaltyApi.listAccounts(filterTier ? { tier_id: filterTier } : undefined),
      ]);
      setStats(s); setTiers(t); setAccounts(a);
    } finally { setLoading(false); }
  }, [filterTier]);

  useEffect(() => { load(); }, [load]);

  const openAccount = async (customerId: string) => {
    setDetailLoading(true);
    setSelectedAccount(null);
    try { setSelectedAccount(await loyaltyApi.getAccount(customerId)); }
    finally { setDetailLoading(false); }
  };

  const enroll = async () => {
    if (!enrollForm.customer_id) { setError("Customer ID required"); return; }
    setSaving(true); setError("");
    try {
      await loyaltyApi.enrollCustomer({ customer_id: enrollForm.customer_id, initial_points: parseInt(enrollForm.initial_points) || 0 });
      setShowEnroll(false); setEnrollForm({ customer_id: "", initial_points: "0" }); await load();
    } catch { setError("Enrollment failed. Customer may already be enrolled."); }
    finally { setSaving(false); }
  };

  const earn = async () => {
    if (!selectedAccount) return;
    if (!earnForm.points && !earnForm.spend_amount) { setError("Enter points or spend amount"); return; }
    setSaving(true); setError("");
    try {
      await loyaltyApi.earnPoints(selectedAccount.customer_id, {
        points: earnForm.points ? parseInt(earnForm.points) : undefined,
        spend_amount: earnForm.spend_amount ? parseFloat(earnForm.spend_amount) : undefined,
        description: earnForm.description || undefined,
      });
      setShowEarn(false); setEarnForm({ points: "", spend_amount: "", description: "" });
      await openAccount(selectedAccount.customer_id); await load();
    } catch { setError("Failed to add points"); }
    finally { setSaving(false); }
  };

  const redeem = async () => {
    if (!selectedAccount || !redeemForm.points) { setError("Points required"); return; }
    setSaving(true); setError("");
    try {
      await loyaltyApi.redeemPoints(selectedAccount.customer_id, {
        points: parseInt(redeemForm.points),
        description: redeemForm.description || undefined,
      });
      setShowRedeem(false); setRedeemForm({ points: "", description: "" });
      await openAccount(selectedAccount.customer_id); await load();
    } catch { setError("Redemption failed. Insufficient points?"); }
    finally { setSaving(false); }
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Customer Loyalty Program</h1>
          <p className="text-xs text-gray-500 mt-0.5">Points, tiers, and rewards for distributor and customer retention.</p>
        </div>
        <button onClick={() => { setShowEnroll(true); setError(""); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Enroll Customer
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Active Members", value: stats.total_members, color: "text-blue-600" },
            { label: "Points Outstanding", value: stats.total_points_outstanding.toLocaleString(), color: "text-amber-600" },
            { label: "Total Transactions", value: stats.total_transactions, color: "text-purple-600" },
          ].map(s => (
            <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tier cards */}
      {tiers.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {tiers.map(t => (
            <div key={t.id} className="bg-white border-2 rounded-xl p-4 shadow-sm"
              style={{ borderColor: t.color }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold" style={{ color: t.color }}>{t.tier_name}</span>
                <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">{t.member_count} members</span>
              </div>
              <p className="text-xs text-gray-500">Min: {t.min_lifetime_points.toLocaleString()} pts</p>
              <p className="text-xs text-gray-500">{t.points_per_100_spend} pts/100 spend</p>
              {t.discount_pct > 0 && <p className="text-xs text-green-600">{t.discount_pct}% discount</p>}
              {(t.perks ?? []).length > 0 && (
                <div className="mt-2 flex gap-1 flex-wrap">
                  {t.perks.map((p, i) => (
                    <span key={i} className="text-xs bg-gray-50 text-gray-500 rounded px-1.5 py-0.5">{p}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Members list */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex gap-3 items-center flex-wrap">
            <select value={filterTier} onChange={e => setFilterTier(e.target.value)}
              className="border rounded px-2 py-1.5 text-sm">
              <option value="">All Tiers</option>
              {tiers.map(t => <option key={t.id} value={t.id}>{t.tier_name}</option>)}
            </select>
            <span className="text-xs text-gray-500">{accounts.length} members</span>
          </div>
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : accounts.length === 0 ? (
            <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
              <p className="text-2xl mb-2">🏆</p>
              <p className="text-sm">No members enrolled yet.</p>
            </div>
          ) : (
            <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {["Customer", "Tier", "Points", "Lifetime", "Last Active", ""].map(h => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {accounts.map(a => (
                    <tr key={a.id} className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => openAccount(a.customer_id)}>
                      <td className="px-4 py-3 font-medium text-gray-800">
                        {a.customer_name ?? "—"}
                        {a.customer_code && <span className="text-xs text-gray-400 ml-1">({a.customer_code})</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-semibold rounded-full px-2 py-0.5 text-white"
                          style={{ backgroundColor: a.tier_color }}>
                          {a.tier_name}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm font-bold text-amber-600">{a.total_points.toLocaleString()}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{a.lifetime_points.toLocaleString()}</td>
                      <td className="px-4 py-3 text-xs text-gray-400">
                        {a.last_activity_at ? new Date(a.last_activity_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-blue-600">View →</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Account detail panel */}
        <div className="bg-white border rounded-lg p-5">
          {detailLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : selectedAccount ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-bold text-gray-900">{selectedAccount.customer_name}</h3>
                  <span className="text-xs font-semibold rounded-full px-2 py-0.5 text-white"
                    style={{ backgroundColor: selectedAccount.tier_color }}>
                    {selectedAccount.tier_name}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div className="bg-amber-50 rounded p-2 text-center">
                    <p className="text-xs text-gray-500">Balance</p>
                    <p className="text-xl font-bold text-amber-600">{selectedAccount.total_points.toLocaleString()}</p>
                  </div>
                  <div className="bg-gray-50 rounded p-2 text-center">
                    <p className="text-xs text-gray-500">Lifetime</p>
                    <p className="text-xl font-bold text-gray-700">{selectedAccount.lifetime_points.toLocaleString()}</p>
                  </div>
                </div>
                {selectedAccount.discount_pct > 0 && (
                  <p className="text-xs text-green-600 mt-1">Tier discount: {selectedAccount.discount_pct}%</p>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={() => { setShowEarn(true); setError(""); }}
                  className="flex-1 rounded bg-green-600 py-1.5 text-xs font-medium text-white hover:bg-green-700">
                  + Earn
                </button>
                <button onClick={() => { setShowRedeem(true); setError(""); }}
                  className="flex-1 rounded bg-red-600 py-1.5 text-xs font-medium text-white hover:bg-red-700">
                  - Redeem
                </button>
              </div>
              <div className="border-t pt-3">
                <p className="text-xs font-semibold text-gray-600 mb-2">Recent Transactions</p>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {selectedAccount.transactions.length === 0 ? (
                    <p className="text-xs text-gray-400">No transactions yet.</p>
                  ) : selectedAccount.transactions.map(t => (
                    <div key={t.id} className="flex items-center justify-between text-xs">
                      <div className="flex-1 min-w-0">
                        <span className={`font-semibold ${TXN_COLORS[t.transaction_type] ?? "text-gray-600"}`}>
                          {t.transaction_type}
                        </span>
                        <span className="text-gray-500 ml-1 truncate">{t.description}</span>
                      </div>
                      <span className={`font-bold ml-2 ${t.points_delta > 0 ? "text-green-600" : "text-red-600"}`}>
                        {t.points_delta > 0 ? "+" : ""}{t.points_delta}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p className="text-2xl mb-2">🏆</p>
              <p className="text-sm">Click a member to view account.</p>
            </div>
          )}
        </div>
      </div>

      {/* Enroll Modal */}
      {showEnroll && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Enroll Customer</h2>
              <button onClick={() => setShowEnroll(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Customer ID (UUID) *</label>
                <input type="text" value={enrollForm.customer_id}
                  onChange={e => setEnrollForm(f => ({ ...f, customer_id: e.target.value }))}
                  placeholder="UUID"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Welcome Bonus Points</label>
                <input type="number" value={enrollForm.initial_points}
                  onChange={e => setEnrollForm(f => ({ ...f, initial_points: e.target.value }))}
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={enroll} disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? "Enrolling…" : "Enroll"}
              </button>
              <button onClick={() => setShowEnroll(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Earn Modal */}
      {showEarn && selectedAccount && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Add Points — {selectedAccount.customer_name}</h2>
              <button onClick={() => setShowEarn(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Points (direct)</label>
                <input type="number" value={earnForm.points}
                  onChange={e => setEarnForm(f => ({ ...f, points: e.target.value }))}
                  placeholder="e.g. 100"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Or: Spend Amount (auto-calc points)</label>
                <input type="number" value={earnForm.spend_amount}
                  onChange={e => setEarnForm(f => ({ ...f, spend_amount: e.target.value }))}
                  placeholder="e.g. 5000"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                <input type="text" value={earnForm.description}
                  onChange={e => setEarnForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="e.g. Order #SO-001"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={earn} disabled={saving}
                className="flex-1 rounded bg-green-600 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
                {saving ? "Adding…" : "Add Points"}
              </button>
              <button onClick={() => setShowEarn(false)}
                className="flex-1 rounded border py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Redeem Modal */}
      {showRedeem && selectedAccount && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm">
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-base font-semibold">Redeem Points</h2>
              <button onClick={() => setShowRedeem(false)} className="text-gray-400 text-xl">×</button>
            </div>
            <div className="p-6 space-y-3">
              {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
              <p className="text-xs text-gray-500">Balance: <strong className="text-amber-600">{selectedAccount.total_points.toLocaleString()} pts</strong></p>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Points to Redeem *</label>
                <input type="number" value={redeemForm.points}
                  onChange={e => setRedeemForm(f => ({ ...f, points: e.target.value }))}
                  placeholder="e.g. 500"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Reward Description</label>
                <input type="text" value={redeemForm.description}
                  onChange={e => setRedeemForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="e.g. Free goods redemption"
                  className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
            <div className="px-6 pb-5 flex gap-3">
              <button onClick={redeem} disabled={saving}
                className="flex-1 rounded bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {saving ? "Redeeming…" : "Redeem Points"}
              </button>
              <button onClick={() => setShowRedeem(false)}
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
