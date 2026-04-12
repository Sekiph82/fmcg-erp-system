"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  pricingApi,
  PricingRule,
  Promotion,
  PricingLevel,
  PromoType,
  LEVEL_COLORS,
} from "@/lib/pricing";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";

type Tab = "rules" | "promotions";

const LEVELS: PricingLevel[] = ["STANDARD", "REGION", "DISTRIBUTOR", "CUSTOMER"];
const PROMO_TYPES: PromoType[] = ["DISCOUNT", "BUNDLE", "VOLUME"];

const emptyRule = {
  product_id: "",
  pricing_level: "STANDARD" as PricingLevel,
  region: "",
  unit_price: "",
  currency: "KES",
  min_quantity: "",
  effective_from: "",
  effective_to: "",
  notes: "",
};

const emptyPromo = {
  code: "",
  name: "",
  promo_type: "DISCOUNT" as PromoType,
  discount_type: "PERCENTAGE" as "PERCENTAGE" | "FIXED_AMOUNT",
  discount_value: "",
  min_order_value: "",
  start_date: new Date().toISOString().split("T")[0],
  end_date: "",
  region: "",
  description: "",
};

const LEVEL_BADGE_VARIANT: Record<PricingLevel, "green" | "blue" | "gray" | "yellow"> = {
  STANDARD: "gray",
  REGION: "blue",
  DISTRIBUTOR: "yellow",
  CUSTOMER: "green",
};

export default function PricingPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("rules");
  const [ruleOpen, setRuleOpen] = useState(false);
  const [promoOpen, setPromoOpen] = useState(false);
  const [ruleForm, setRuleForm] = useState(emptyRule);
  const [promoForm, setPromoForm] = useState(emptyPromo);
  const [levelFilter, setLevelFilter] = useState<PricingLevel | "ALL">("ALL");

  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ["pricing-rules", levelFilter],
    queryFn: () =>
      pricingApi.listRules({
        ...(levelFilter !== "ALL" ? { pricing_level: levelFilter } : {}),
        active_only: true,
      }),
  });

  const { data: promotions = [], isLoading: promosLoading } = useQuery({
    queryKey: ["promotions"],
    queryFn: () => pricingApi.listPromotions(),
  });

  const createRule = useMutation({
    mutationFn: () =>
      pricingApi.createRule({
        ...ruleForm,
        unit_price: parseFloat(ruleForm.unit_price as string) || 0,
        min_quantity: ruleForm.min_quantity ? parseInt(ruleForm.min_quantity as string) : undefined,
        region: ruleForm.region || undefined,
        effective_from: ruleForm.effective_from || undefined,
        effective_to: ruleForm.effective_to || undefined,
        notes: ruleForm.notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pricing-rules"] });
      setRuleOpen(false);
      setRuleForm(emptyRule);
    },
  });

  const createPromo = useMutation({
    mutationFn: () =>
      pricingApi.createPromotion({
        ...promoForm,
        discount_value: promoForm.discount_value ? parseFloat(promoForm.discount_value as string) : undefined,
        min_order_value: promoForm.min_order_value ? parseFloat(promoForm.min_order_value as string) : undefined,
        region: promoForm.region || undefined,
        description: promoForm.description || undefined,
        product_ids: [],
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["promotions"] });
      setPromoOpen(false);
      setPromoForm(emptyPromo);
    },
  });

  const deactivateRule = useMutation({
    mutationFn: (id: string) => pricingApi.updateRule(id, { is_active: false }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pricing-rules"] }),
  });

  const deactivatePromo = useMutation({
    mutationFn: (id: string) => pricingApi.updatePromotion(id, { is_active: false }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promotions"] }),
  });

  const setR = (k: keyof typeof emptyRule, v: unknown) => setRuleForm((f) => ({ ...f, [k]: v }));
  const setP = (k: keyof typeof emptyPromo, v: unknown) => setPromoForm((f) => ({ ...f, [k]: v }));

  const today = new Date().toISOString().split("T")[0];
  const activePromos = promotions.filter((p) => p.is_active && p.end_date >= today).length;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pricing & Promotions</h1>
          <p className="text-sm text-gray-500 mt-1">Tiered pricing · Distributor rates · Volume discounts · Bundles</p>
        </div>
        <div className="flex gap-2">
          {tab === "rules" && <Button onClick={() => setRuleOpen(true)}>+ Pricing Rule</Button>}
          {tab === "promotions" && <Button onClick={() => setPromoOpen(true)}>+ Promotion</Button>}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "Standard Rules", value: rules.filter((r) => r.pricing_level === "STANDARD").length, color: "text-gray-700" },
          { label: "Region Rules", value: rules.filter((r) => r.pricing_level === "REGION").length, color: "text-blue-600" },
          { label: "Distributor Rules", value: rules.filter((r) => r.pricing_level === "DISTRIBUTOR").length, color: "text-purple-600" },
          { label: "Active Promos", value: activePromos, color: "text-green-600" },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm text-center">
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            <p className="text-xs text-gray-500 mt-1">{k.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {[
          { id: "rules" as Tab, label: "Pricing Rules" },
          { id: "promotions" as Tab, label: "Promotions" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Rules Tab */}
      {tab === "rules" && (
        <>
          <div className="flex flex-wrap gap-2 mb-4">
            {(["ALL", ...LEVELS] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLevelFilter(l)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  levelFilter === l ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {l}
              </button>
            ))}
          </div>
          {rulesLoading ? (
            <Spinner />
          ) : rules.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">No pricing rules found.</p>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <PricingRuleRow
                  key={rule.id}
                  rule={rule}
                  onDeactivate={() => deactivateRule.mutate(rule.id)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Promotions Tab */}
      {tab === "promotions" && (
        promosLoading ? (
          <Spinner />
        ) : promotions.length === 0 ? (
          <p className="text-gray-400 text-sm py-8 text-center">No promotions found.</p>
        ) : (
          <div className="space-y-3">
            {promotions.map((promo) => (
              <PromoCard
                key={promo.id}
                promo={promo}
                today={today}
                onDeactivate={() => deactivatePromo.mutate(promo.id)}
              />
            ))}
          </div>
        )
      )}

      {/* Create Pricing Rule Modal */}
      <Modal open={ruleOpen} onClose={() => setRuleOpen(false)} title="New Pricing Rule">
        <form onSubmit={(e) => { e.preventDefault(); createRule.mutate(); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pricing Level</label>
            <div className="grid grid-cols-2 gap-2">
              {LEVELS.map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setR("pricing_level", l)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium text-left transition-colors ${
                    ruleForm.pricing_level === l
                      ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  <span className={`inline-block rounded px-1.5 py-0.5 text-xs ${LEVEL_COLORS[l]} mr-1`}>{l}</span>
                </button>
              ))}
            </div>
          </div>

          <Input
            label="Product ID *"
            value={ruleForm.product_id}
            onChange={(e) => setR("product_id", e.target.value)}
            required
            placeholder="Product UUID or SKU"
          />

          {ruleForm.pricing_level === "REGION" && (
            <Input
              label="Region *"
              value={ruleForm.region}
              onChange={(e) => setR("region", e.target.value)}
              placeholder="e.g. Nairobi, Coast, Western"
            />
          )}

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Unit Price *"
              type="number"
              step="0.01"
              value={ruleForm.unit_price}
              onChange={(e) => setR("unit_price", e.target.value)}
              required
            />
            <Input
              label="Currency"
              value={ruleForm.currency}
              onChange={(e) => setR("currency", e.target.value)}
              placeholder="KES"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Min Quantity"
              type="number"
              value={ruleForm.min_quantity}
              onChange={(e) => setR("min_quantity", e.target.value)}
              placeholder="0 = no minimum"
            />
            <div />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Effective From"
              type="date"
              value={ruleForm.effective_from}
              onChange={(e) => setR("effective_from", e.target.value)}
            />
            <Input
              label="Effective To"
              type="date"
              value={ruleForm.effective_to}
              onChange={(e) => setR("effective_to", e.target.value)}
            />
          </div>

          <Input
            label="Notes"
            value={ruleForm.notes}
            onChange={(e) => setR("notes", e.target.value)}
          />

          {createRule.error && <p className="text-sm text-red-600">Failed to create rule.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setRuleOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createRule.isPending}>Create Rule</Button>
          </div>
        </form>
      </Modal>

      {/* Create Promotion Modal */}
      <Modal open={promoOpen} onClose={() => setPromoOpen(false)} title="New Promotion">
        <form onSubmit={(e) => { e.preventDefault(); createPromo.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Code *"
              value={promoForm.code}
              onChange={(e) => setP("code", e.target.value)}
              required
              placeholder="PROMO2024"
            />
            <Input
              label="Name *"
              value={promoForm.name}
              onChange={(e) => setP("name", e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Promo Type</label>
            <div className="grid grid-cols-3 gap-2">
              {PROMO_TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setP("promo_type", t)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                    promoForm.promo_type === t
                      ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  {t === "DISCOUNT" ? "% Discount" : t === "BUNDLE" ? "Buy X Get Y" : "Volume"}
                </button>
              ))}
            </div>
          </div>

          {promoForm.promo_type === "DISCOUNT" && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Discount Type</label>
                <select
                  value={promoForm.discount_type}
                  onChange={(e) => setP("discount_type", e.target.value)}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="PERCENTAGE">Percentage %</option>
                  <option value="FIXED_AMOUNT">Fixed Amount</option>
                </select>
              </div>
              <Input
                label="Discount Value"
                type="number"
                step="0.01"
                value={promoForm.discount_value}
                onChange={(e) => setP("discount_value", e.target.value)}
                placeholder={promoForm.discount_type === "PERCENTAGE" ? "10" : "100"}
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Start Date *"
              type="date"
              value={promoForm.start_date}
              onChange={(e) => setP("start_date", e.target.value)}
              required
            />
            <Input
              label="End Date *"
              type="date"
              value={promoForm.end_date}
              onChange={(e) => setP("end_date", e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Min Order Value"
              type="number"
              value={promoForm.min_order_value}
              onChange={(e) => setP("min_order_value", e.target.value)}
              placeholder="0 = no minimum"
            />
            <Input
              label="Region"
              value={promoForm.region}
              onChange={(e) => setP("region", e.target.value)}
              placeholder="Leave blank for all regions"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={promoForm.description}
              onChange={(e) => setP("description", e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {createPromo.error && <p className="text-sm text-red-600">Failed to create promotion.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setPromoOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createPromo.isPending}>Create Promotion</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function PricingRuleRow({ rule, onDeactivate }: { rule: PricingRule; onDeactivate: () => void }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${LEVEL_COLORS[rule.pricing_level]}`}>
            {rule.pricing_level}
          </span>
          <div>
            <p className="text-sm font-medium text-gray-800">
              {rule.product_name ?? rule.product_id.slice(0, 8)}
              {rule.region && <span className="text-gray-400 ml-2">· {rule.region}</span>}
              {rule.distributor_name && <span className="text-gray-400 ml-2">· {rule.distributor_name}</span>}
              {rule.customer_name && <span className="text-gray-400 ml-2">· {rule.customer_name}</span>}
            </p>
            <p className="text-xs text-gray-400">
              {rule.min_quantity ? `Min qty: ${rule.min_quantity}` : "Any qty"}
              {rule.effective_from && <span> · From {rule.effective_from}</span>}
              {rule.effective_to && <span> · To {rule.effective_to}</span>}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-lg font-bold text-gray-900">{rule.currency} {rule.unit_price.toLocaleString()}</p>
          <button
            onClick={onDeactivate}
            className="text-xs text-red-400 hover:text-red-600 transition-colors"
          >
            Deactivate
          </button>
        </div>
      </div>
    </div>
  );
}

function PromoCard({ promo, today, onDeactivate }: { promo: Promotion; today: string; onDeactivate: () => void }) {
  const isActive = promo.is_active && promo.end_date >= today;
  const isExpired = promo.end_date < today;

  return (
    <div className={`rounded-xl border p-4 shadow-sm ${isActive ? "border-green-100 bg-white" : "border-gray-100 bg-gray-50 opacity-70"}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm font-bold text-gray-900">{promo.code}</span>
            <Badge
              label={isExpired ? "Expired" : isActive ? "Active" : "Inactive"}
              variant={isExpired ? "red" : isActive ? "green" : "gray"}
            />
            <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
              promo.promo_type === "DISCOUNT" ? "bg-blue-100 text-blue-700" :
              promo.promo_type === "BUNDLE" ? "bg-purple-100 text-purple-700" :
              "bg-orange-100 text-orange-700"
            }`}>
              {promo.promo_type}
            </span>
          </div>
          <p className="text-sm text-gray-700 font-medium">{promo.name}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {promo.start_date} → {promo.end_date}
            {promo.discount_value && (
              <span> · {promo.discount_type === "PERCENTAGE" ? `${promo.discount_value}%` : `KES ${promo.discount_value}`} off</span>
            )}
            {promo.min_order_value && <span> · Min order KES {promo.min_order_value.toLocaleString()}</span>}
            {promo.region && <span> · {promo.region}</span>}
          </p>
          {promo.description && <p className="text-xs text-gray-400 mt-1">{promo.description}</p>}
        </div>
        {isActive && (
          <button
            onClick={onDeactivate}
            className="text-xs text-red-400 hover:text-red-600 transition-colors shrink-0"
          >
            Deactivate
          </button>
        )}
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  );
}
