"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  promoApi, PromoScheme, SchemeStatus,
  SCHEME_TYPE_LABEL, REWARD_TYPE_LABEL, TRIGGER_BASIS_LABEL,
  STATUS_BADGE, fmtCurrency,
} from "@/lib/promotions";
import Link from "next/link";

export default function SchemeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: scheme, isLoading } = useQuery({
    queryKey: ["promo-scheme", id],
    queryFn: () => promoApi.getScheme(id),
  });

  const activate = useMutation({
    mutationFn: () => promoApi.activateScheme(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-scheme", id] }),
  });

  const suspend = useMutation({
    mutationFn: () => promoApi.updateSchemeStatus(id, "SUSPENDED"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promo-scheme", id] }),
  });

  if (isLoading) return <div className="p-6 text-gray-400">Loading…</div>;
  if (!scheme) return <div className="p-6 text-red-400">Scheme not found.</div>;

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/dashboard/promotions/schemes" className="text-xs text-gray-500 hover:text-indigo-400">← Back to Schemes</Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{scheme.scheme_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="font-mono text-xs text-indigo-300">{scheme.scheme_code}</span>
            <span className="text-xs text-gray-400">{SCHEME_TYPE_LABEL[scheme.scheme_type]}</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[scheme.status]}`}>{scheme.status}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {scheme.status === "DRAFT" && (
            <button onClick={() => activate.mutate()} disabled={activate.isPending} className="glow-button">
              {activate.isPending ? "Activating…" : "Activate"}
            </button>
          )}
          {scheme.status === "ACTIVE" && (
            <button onClick={() => suspend.mutate()} disabled={suspend.isPending} className="glow-button-secondary">
              {suspend.isPending ? "Suspending…" : "Suspend"}
            </button>
          )}
        </div>
      </div>

      {/* Header info */}
      <div className="liquid-glass p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div><p className="text-xs text-gray-500">Valid From</p><p className="text-sm font-medium text-gray-200">{scheme.valid_from}</p></div>
        <div><p className="text-xs text-gray-500">Valid To</p><p className="text-sm font-medium text-gray-200">{scheme.valid_to}</p></div>
        <div><p className="text-xs text-gray-500">Priority</p><p className="text-sm font-medium text-gray-200">{scheme.priority_rank}</p></div>
        <div>
          <p className="text-xs text-gray-500">Stacking</p>
          <p className="text-sm font-medium">
            {scheme.stackable ? <span className="text-green-400">Stackable</span> : scheme.exclusive ? <span className="text-red-400">Exclusive</span> : <span className="text-gray-400">Non-stack</span>}
          </p>
        </div>
        <div><p className="text-xs text-gray-500">Orders Applied</p><p className="text-sm font-bold text-blue-400">{scheme.usage_count}</p></div>
        <div><p className="text-xs text-gray-500">Total Cost</p><p className="text-sm font-bold text-orange-400">{fmtCurrency(scheme.total_cost)}</p></div>
        {scheme.notes && <div className="col-span-2"><p className="text-xs text-gray-500">Notes</p><p className="text-sm text-gray-300">{scheme.notes}</p></div>}
      </div>

      {/* Eligibility Scopes */}
      {scheme.eligibility_scopes.length > 0 && (
        <div className="liquid-glass p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Eligibility Scope</h2>
          {scheme.eligibility_scopes.map((e) => (
            <div key={e.id} className="grid grid-cols-3 gap-2 text-xs">
              {e.applies_to_channel && <div><span className="text-gray-500">Channel:</span> <span className="text-gray-300">{e.applies_to_channel}</span></div>}
              {e.applies_to_region && <div><span className="text-gray-500">Region:</span> <span className="text-gray-300">{e.applies_to_region}</span></div>}
              {e.applies_to_customer_group && <div><span className="text-gray-500">Customer Group:</span> <span className="text-gray-300">{e.applies_to_customer_group}</span></div>}
              {e.applies_to_item_category && <div><span className="text-gray-500">Category:</span> <span className="text-gray-300">{e.applies_to_item_category}</span></div>}
              {e.applies_to_brand && <div><span className="text-gray-500">Brand:</span> <span className="text-gray-300">{e.applies_to_brand}</span></div>}
              {e.min_order_value && <div><span className="text-gray-500">Min Order:</span> <span className="text-gray-300">{fmtCurrency(e.min_order_value)}</span></div>}
              {e.min_order_qty && <div><span className="text-gray-500">Min Qty:</span> <span className="text-gray-300">{e.min_order_qty}</span></div>}
            </div>
          ))}
        </div>
      )}

      {/* Rule Lines */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Promotion Rules ({scheme.rule_lines.length})</h2>
        {scheme.rule_lines.length === 0 ? (
          <p className="text-sm text-gray-400">No rules configured. This scheme will never trigger.</p>
        ) : scheme.rule_lines.map((rule, i) => (
          <div key={rule.id} className="glass-panel rounded-xl border border-blue-900/30 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-400">Rule {i + 1}</span>
              <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-100 text-indigo-700">
                {TRIGGER_BASIS_LABEL[rule.trigger_basis]}
              </span>
              <span className="px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-700">
                {REWARD_TYPE_LABEL[rule.reward_type]}
              </span>
              {rule.repeatable && <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">Repeatable</span>}
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {rule.trigger_item_name && <div><span className="text-gray-500">Item:</span> <span className="text-gray-300">{rule.trigger_item_name}</span></div>}
              {rule.trigger_category && <div><span className="text-gray-500">Category:</span> <span className="text-gray-300">{rule.trigger_category}</span></div>}
              {rule.trigger_brand && <div><span className="text-gray-500">Brand:</span> <span className="text-gray-300">{rule.trigger_brand}</span></div>}
              {Number(rule.min_trigger_qty) > 0 && <div><span className="text-gray-500">Min Qty:</span> <span className="text-gray-300">{rule.min_trigger_qty}</span></div>}
              {Number(rule.min_trigger_value) > 0 && <div><span className="text-gray-500">Min Value:</span> <span className="text-gray-300">{fmtCurrency(Number(rule.min_trigger_value))}</span></div>}
              {rule.reward_percent && <div><span className="text-gray-500">Discount:</span> <span className="text-green-400">{rule.reward_percent}%</span></div>}
              {rule.reward_amount && <div><span className="text-gray-500">Amount Off:</span> <span className="text-green-400">{fmtCurrency(Number(rule.reward_amount))}</span></div>}
              {rule.reward_qty && <div><span className="text-gray-500">Free Qty:</span> <span className="text-green-400">{rule.reward_qty} units</span></div>}
              {rule.reward_item_name && <div><span className="text-gray-500">Free Item:</span> <span className="text-gray-300">{rule.reward_item_name}</span></div>}
              {rule.reward_special_unit_price && <div><span className="text-gray-500">Special Price:</span> <span className="text-green-400">{fmtCurrency(Number(rule.reward_special_unit_price))}</span></div>}
            </div>
            {rule.notes && <p className="text-xs text-gray-400">{rule.notes}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
