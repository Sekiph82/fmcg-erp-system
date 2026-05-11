"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AccountingPostingBatch,
  AccountingPostingRule,
  CurrencyRevaluationRun,
  FiscalYear,
  PaymentAllocation,
  financeApi,
} from "@/lib/finance";

const STATUS_PILL: Record<string, string> = {
  OPEN: "bg-green-100 text-green-700",
  CLOSING: "bg-yellow-100 text-yellow-700",
  CLOSED: "bg-gray-100 text-gray-700",
  LOCKED: "bg-red-100 text-red-700",
  DRAFT: "bg-gray-100 text-gray-600",
  POSTED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
  REVERSED: "bg-orange-100 text-orange-700",
};

function statusClass(status?: string) {
  return STATUS_PILL[status ?? ""] ?? "bg-gray-100 text-gray-600";
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-gray-500 mb-1">{label}</span>
      {children}
    </label>
  );
}

function inputClass() {
  return "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300";
}

export default function AccountingControlsPage() {
  const qc = useQueryClient();
  const [fiscalYear, setFiscalYear] = useState({
    year_code: "",
    start_date: "",
    end_date: "",
    base_currency: "KES",
  });
  const [postingRule, setPostingRule] = useState({
    source_module: "",
    source_event: "",
    rule_name: "",
    debit_account_id: "",
    credit_account_id: "",
    priority: "100",
  });

  const fiscalYears = useQuery<FiscalYear[]>({
    queryKey: ["accounting-fiscal-years"],
    queryFn: financeApi.listFiscalYears,
    staleTime: 30_000,
  });
  const postingRules = useQuery<AccountingPostingRule[]>({
    queryKey: ["accounting-posting-rules"],
    queryFn: () => financeApi.listPostingRules(),
    staleTime: 30_000,
  });
  const postingBatches = useQuery<AccountingPostingBatch[]>({
    queryKey: ["accounting-posting-batches"],
    queryFn: () => financeApi.listPostingBatches({ limit: 25 }),
    staleTime: 30_000,
  });
  const paymentAllocations = useQuery<PaymentAllocation[]>({
    queryKey: ["accounting-payment-allocations"],
    queryFn: () => financeApi.listPaymentAllocations({ limit: 25 }),
    staleTime: 30_000,
  });
  const currencyRevaluations = useQuery<CurrencyRevaluationRun[]>({
    queryKey: ["accounting-currency-revaluations"],
    queryFn: () => financeApi.listCurrencyRevaluations({ limit: 25 }),
    staleTime: 30_000,
  });

  const createFiscalYear = useMutation({
    mutationFn: financeApi.createFiscalYear,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounting-fiscal-years"] });
      setFiscalYear({ year_code: "", start_date: "", end_date: "", base_currency: "KES" });
    },
  });

  const createPostingRule = useMutation({
    mutationFn: financeApi.createPostingRule,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounting-posting-rules"] });
      setPostingRule({
        source_module: "",
        source_event: "",
        rule_name: "",
        debit_account_id: "",
        credit_account_id: "",
        priority: "100",
      });
    },
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Accounting Controls</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Fiscal years, posting rules, posting batches, allocations, and currency revaluation controls.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h2 className="font-semibold text-gray-800">Fiscal Years</h2>
          <span className="text-xs text-gray-400">{fiscalYears.data?.length ?? 0} records</span>
        </div>
        <div className="grid md:grid-cols-5 gap-3 mb-5">
          <Field label="Code">
            <input className={inputClass()} value={fiscalYear.year_code} placeholder="FY2026"
              onChange={(e) => setFiscalYear({ ...fiscalYear, year_code: e.target.value })} />
          </Field>
          <Field label="Start">
            <input className={inputClass()} type="date" value={fiscalYear.start_date}
              onChange={(e) => setFiscalYear({ ...fiscalYear, start_date: e.target.value })} />
          </Field>
          <Field label="End">
            <input className={inputClass()} type="date" value={fiscalYear.end_date}
              onChange={(e) => setFiscalYear({ ...fiscalYear, end_date: e.target.value })} />
          </Field>
          <Field label="Currency">
            <input className={inputClass()} value={fiscalYear.base_currency}
              onChange={(e) => setFiscalYear({ ...fiscalYear, base_currency: e.target.value.toUpperCase() })} />
          </Field>
          <button
            className="self-end bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            disabled={!fiscalYear.year_code || !fiscalYear.start_date || !fiscalYear.end_date || createFiscalYear.isPending}
            onClick={() => createFiscalYear.mutate(fiscalYear)}
          >
            {createFiscalYear.isPending ? "Creating..." : "Create"}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Code</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Dates</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Currency</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {fiscalYears.isLoading && <tr><td colSpan={4} className="py-6 text-center text-gray-400">Loading...</td></tr>}
              {!fiscalYears.isLoading && (fiscalYears.data ?? []).length === 0 && (
                <tr><td colSpan={4} className="py-6 text-center text-gray-400">No fiscal years found.</td></tr>
              )}
              {(fiscalYears.data ?? []).map((fy) => (
                <tr key={fy.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-semibold text-gray-900">{fy.year_code}</td>
                  <td className="px-4 py-3 text-gray-600">{fy.start_date} to {fy.end_date}</td>
                  <td className="px-4 py-3 text-gray-600">{fy.base_currency}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${statusClass(fy.status)}`}>{fy.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Posting Rules</h2>
          <div className="grid md:grid-cols-2 gap-3 mb-5">
            <Field label="Module">
              <input className={inputClass()} value={postingRule.source_module}
                onChange={(e) => setPostingRule({ ...postingRule, source_module: e.target.value })} />
            </Field>
            <Field label="Event">
              <input className={inputClass()} value={postingRule.source_event}
                onChange={(e) => setPostingRule({ ...postingRule, source_event: e.target.value })} />
            </Field>
            <Field label="Rule Name">
              <input className={inputClass()} value={postingRule.rule_name}
                onChange={(e) => setPostingRule({ ...postingRule, rule_name: e.target.value })} />
            </Field>
            <Field label="Priority">
              <input className={inputClass()} type="number" value={postingRule.priority}
                onChange={(e) => setPostingRule({ ...postingRule, priority: e.target.value })} />
            </Field>
            <Field label="Debit Account ID">
              <input className={inputClass()} value={postingRule.debit_account_id}
                onChange={(e) => setPostingRule({ ...postingRule, debit_account_id: e.target.value })} />
            </Field>
            <Field label="Credit Account ID">
              <input className={inputClass()} value={postingRule.credit_account_id}
                onChange={(e) => setPostingRule({ ...postingRule, credit_account_id: e.target.value })} />
            </Field>
          </div>
          <button
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            disabled={!postingRule.source_module || !postingRule.source_event || !postingRule.rule_name || createPostingRule.isPending}
            onClick={() => createPostingRule.mutate({
              source_module: postingRule.source_module,
              source_event: postingRule.source_event,
              rule_name: postingRule.rule_name,
              debit_account_id: postingRule.debit_account_id || undefined,
              credit_account_id: postingRule.credit_account_id || undefined,
              priority: Number(postingRule.priority || 100),
            })}
          >
            {createPostingRule.isPending ? "Creating..." : "Create Rule"}
          </button>
          <div className="mt-5 divide-y divide-gray-50">
            {(postingRules.data ?? []).slice(0, 8).map((rule) => (
              <div key={rule.id} className="py-3">
                <p className="text-sm font-semibold text-gray-900">{rule.rule_name}</p>
                <p className="text-xs text-gray-400">{rule.source_module} / {rule.source_event} / priority {rule.priority}</p>
              </div>
            ))}
            {!postingRules.isLoading && (postingRules.data ?? []).length === 0 && (
              <p className="text-sm text-gray-400 py-4">No posting rules found.</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <SummaryList title="Posting Batches" empty="No posting batches found."
            rows={(postingBatches.data ?? []).map((batch) => ({
              id: batch.id,
              title: `${batch.source_module} / ${batch.source_event}`,
              detail: batch.source_ref || batch.source_id,
              status: batch.status,
            }))} />
          <SummaryList title="Payment Allocations" empty="No allocations found."
            rows={(paymentAllocations.data ?? []).map((allocation) => ({
              id: allocation.id,
              title: `${allocation.party_type} ${allocation.allocated_amount}`,
              detail: allocation.allocation_date,
              status: allocation.party_type,
            }))} />
          <SummaryList title="Currency Revaluations" empty="No revaluation runs found."
            rows={(currencyRevaluations.data ?? []).map((run) => ({
              id: run.id,
              title: `${run.run_no} / ${run.currency}`,
              detail: run.as_of_date,
              status: run.status,
            }))} />
        </div>
      </section>
    </div>
  );
}

function SummaryList({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: { id: string; title: string; detail?: string; status?: string }[];
  empty: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-50">
        <h2 className="font-semibold text-gray-800">{title}</h2>
      </div>
      <div className="divide-y divide-gray-50">
        {rows.length === 0 && <p className="text-sm text-gray-400 p-4">{empty}</p>}
        {rows.slice(0, 6).map((row) => (
          <div key={row.id} className="flex items-center justify-between gap-3 px-5 py-3">
            <div>
              <p className="text-sm font-medium text-gray-900">{row.title}</p>
              <p className="text-xs text-gray-400">{row.detail || "-"}</p>
            </div>
            {row.status && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${statusClass(row.status)}`}>{row.status}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
