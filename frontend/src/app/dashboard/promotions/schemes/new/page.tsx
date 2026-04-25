"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  promoApi, SchemeType, TriggerBasis, RewardType,
  SCHEME_TYPE_LABEL, REWARD_TYPE_LABEL, TRIGGER_BASIS_LABEL,
} from "@/lib/promotions";

interface RuleForm {
  trigger_basis: TriggerBasis;
  trigger_category: string;
  trigger_brand: string;
  min_trigger_qty: string;
  min_trigger_value: string;
  reward_type: RewardType;
  reward_qty: string;
  reward_percent: string;
  reward_amount: string;
  reward_special_unit_price: string;
  max_reward_qty: string;
  repeatable: boolean;
  notes: string;
}

const BLANK_RULE: RuleForm = {
  trigger_basis: "SKU", trigger_category: "", trigger_brand: "",
  min_trigger_qty: "0", min_trigger_value: "0",
  reward_type: "PERCENT_DISCOUNT",
  reward_qty: "", reward_percent: "", reward_amount: "",
  reward_special_unit_price: "", max_reward_qty: "", repeatable: false, notes: "",
};

export default function NewSchemePage() {
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    scheme_code: "", scheme_name: "", scheme_type: "PERCENT_DISCOUNT" as SchemeType,
    valid_from: today, valid_to: "",
    priority_rank: "10", stackable: false, exclusive: false,
    requires_approval_override: false, notes: "",
  });
  const [eligScope, setEligScope] = useState({
    applies_to_channel: "", applies_to_region: "", applies_to_customer_group: "",
    applies_to_item_category: "", applies_to_brand: "",
    min_order_qty: "", min_order_value: "",
  });
  const [rules, setRules] = useState<RuleForm[]>([{ ...BLANK_RULE }]);

  const create = useMutation({
    mutationFn: () => promoApi.createScheme({
      ...form,
      priority_rank: Number(form.priority_rank),
      eligibility_scopes: [{
        applies_to_channel: eligScope.applies_to_channel || undefined,
        applies_to_region: eligScope.applies_to_region || undefined,
        applies_to_customer_group: eligScope.applies_to_customer_group || undefined,
        applies_to_item_category: eligScope.applies_to_item_category || undefined,
        applies_to_brand: eligScope.applies_to_brand || undefined,
        min_order_qty: eligScope.min_order_qty ? Number(eligScope.min_order_qty) : undefined,
        min_order_value: eligScope.min_order_value ? Number(eligScope.min_order_value) : undefined,
        active: true,
      }].filter((e) => Object.values(e).some((v) => v !== undefined && v !== "")),
      rule_lines: rules.map((r) => ({
        trigger_basis: r.trigger_basis,
        trigger_category: r.trigger_category || undefined,
        trigger_brand: r.trigger_brand || undefined,
        min_trigger_qty: Number(r.min_trigger_qty),
        min_trigger_value: Number(r.min_trigger_value),
        reward_type: r.reward_type,
        reward_qty: r.reward_qty ? Number(r.reward_qty) : undefined,
        reward_percent: r.reward_percent ? Number(r.reward_percent) : undefined,
        reward_amount: r.reward_amount ? Number(r.reward_amount) : undefined,
        reward_special_unit_price: r.reward_special_unit_price ? Number(r.reward_special_unit_price) : undefined,
        max_reward_qty: r.max_reward_qty ? Number(r.max_reward_qty) : undefined,
        repeatable: r.repeatable,
        notes: r.notes || undefined,
        tiers: [],
      })),
    }),
    onSuccess: (scheme) => router.push(`/dashboard/promotions/schemes/${scheme.id}`),
  });

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));
  const setElig = (k: string, v: string) => setEligScope((e) => ({ ...e, [k]: v }));
  const setRule = (i: number, k: keyof RuleForm, v: any) =>
    setRules(rules.map((r, idx) => idx === i ? { ...r, [k]: v } : r));
  const addRule = () => setRules([...rules, { ...BLANK_RULE }]);
  const removeRule = (i: number) => setRules(rules.filter((_, idx) => idx !== i));

  const canSubmit = form.scheme_code && form.scheme_name && form.valid_from && form.valid_to;

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">New Promotional Scheme</h1>

      {create.isError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          Failed to create scheme. Check required fields.
        </div>
      )}

      {/* Header */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Scheme Header</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Scheme Code *</label>
            <input type="text" value={form.scheme_code} onChange={(e) => set("scheme_code", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" placeholder="e.g. PROMO-Q4-2024" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Scheme Name *</label>
            <input type="text" value={form.scheme_name} onChange={(e) => set("scheme_name", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Type *</label>
            <select value={form.scheme_type} onChange={(e) => set("scheme_type", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {Object.entries(SCHEME_TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Priority Rank (lower = first)</label>
            <input type="number" value={form.priority_rank} onChange={(e) => set("priority_rank", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="1" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Valid From *</label>
            <input type="date" value={form.valid_from} onChange={(e) => set("valid_from", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Valid To *</label>
            <input type="date" value={form.valid_to} onChange={(e) => set("valid_to", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="col-span-2 flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input type="checkbox" checked={form.stackable} onChange={(e) => set("stackable", e.target.checked)} className="rounded" />
              Stackable (can combine with other promos)
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input type="checkbox" checked={form.exclusive} onChange={(e) => set("exclusive", e.target.checked)} className="rounded" />
              Exclusive (blocks other promos)
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input type="checkbox" checked={form.requires_approval_override} onChange={(e) => set("requires_approval_override", e.target.checked)} className="rounded" />
              Requires Override Approval
            </label>
          </div>
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-xs text-gray-500">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" rows={2} />
          </div>
        </div>
      </div>

      {/* Eligibility */}
      <div className="liquid-glass p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Eligibility Scope (optional — leave blank for open)</h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            ["applies_to_channel", "Channel (e.g. modern-trade)"],
            ["applies_to_region", "Region"],
            ["applies_to_customer_group", "Customer Group"],
            ["applies_to_item_category", "Item Category"],
            ["applies_to_brand", "Brand"],
          ].map(([k, l]) => (
            <div key={k} className="flex flex-col gap-1">
              <label className="text-xs text-gray-500">{l}</label>
              <input type="text" value={(eligScope as any)[k]} onChange={(e) => setElig(k, e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          ))}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Min Order Value (KES)</label>
            <input type="number" value={eligScope.min_order_value} onChange={(e) => setElig("min_order_value", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Min Order Qty</label>
            <input type="number" value={eligScope.min_order_qty} onChange={(e) => setElig("min_order_qty", e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
          </div>
        </div>
      </div>

      {/* Rule Lines */}
      <div className="liquid-glass p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Promotion Rules</h2>
          <button type="button" onClick={addRule} className="glow-button-secondary text-xs !py-1">+ Add Rule</button>
        </div>
        {rules.map((rule, i) => (
          <div key={i} className="glass-panel p-4 space-y-3 rounded-xl border border-blue-900/30">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-400 uppercase">Rule {i + 1}</span>
              {rules.length > 1 && (
                <button onClick={() => removeRule(i)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Trigger Basis</label>
                <select value={rule.trigger_basis} onChange={(e) => setRule(i, "trigger_basis", e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {Object.entries(TRIGGER_BASIS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Reward Type</label>
                <select value={rule.reward_type} onChange={(e) => setRule(i, "reward_type", e.target.value as RewardType)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  {Object.entries(REWARD_TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              {(rule.trigger_basis === "CATEGORY") && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Category</label>
                  <input type="text" value={rule.trigger_category} onChange={(e) => setRule(i, "trigger_category", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              )}
              {(rule.trigger_basis === "BRAND") && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Brand</label>
                  <input type="text" value={rule.trigger_brand} onChange={(e) => setRule(i, "trigger_brand", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              )}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Min Trigger Qty</label>
                <input type="number" value={rule.min_trigger_qty} onChange={(e) => setRule(i, "min_trigger_qty", e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-gray-500">Min Trigger Value (KES)</label>
                <input type="number" value={rule.min_trigger_value} onChange={(e) => setRule(i, "min_trigger_value", e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
              </div>
              {rule.reward_type === "PERCENT_DISCOUNT" && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Discount %</label>
                  <input type="number" value={rule.reward_percent} onChange={(e) => setRule(i, "reward_percent", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" max="100" />
                </div>
              )}
              {(rule.reward_type === "FIXED_DISCOUNT" || rule.reward_type === "BUNDLE_PRICE") && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Discount Amount (KES)</label>
                  <input type="number" value={rule.reward_amount} onChange={(e) => setRule(i, "reward_amount", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
                </div>
              )}
              {rule.reward_type === "FREE_GOODS" && (
                <>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500">Free Qty</label>
                    <input type="number" value={rule.reward_qty} onChange={(e) => setRule(i, "reward_qty", e.target.value)}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-gray-500">Max Reward Qty (cap)</label>
                    <input type="number" value={rule.max_reward_qty} onChange={(e) => setRule(i, "max_reward_qty", e.target.value)}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
                  </div>
                </>
              )}
              {rule.reward_type === "SPECIAL_PRICE" && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-500">Special Unit Price (KES)</label>
                  <input type="number" value={rule.reward_special_unit_price} onChange={(e) => setRule(i, "reward_special_unit_price", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm" min="0" />
                </div>
              )}
              <div className="flex items-center gap-2 col-span-2">
                <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
                  <input type="checkbox" checked={rule.repeatable} onChange={(e) => setRule(i, "repeatable", e.target.checked)} className="rounded" />
                  Repeatable (apply for each multiple of trigger qty)
                </label>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button onClick={() => create.mutate()} disabled={create.isPending || !canSubmit} className="glow-button">
          {create.isPending ? "Creating…" : "Create Scheme"}
        </button>
        <button onClick={() => router.back()} className="glow-button-secondary">Cancel</button>
      </div>
    </div>
  );
}
