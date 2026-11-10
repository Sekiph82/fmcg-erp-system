"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { mfApi, Consumption, FlowTransaction, Reservation, ReservationLine, FLOW_STATUS_COLORS } from "@/lib/materialFlow";

function outstanding(line: ReservationLine): number {
  return Math.max(0, Number(line.quantity_reserved) - Number(line.quantity_issued));
}

export default function IssuePage() {
  const qc = useQueryClient();
  const [reservationId, setReservationId] = useState("");
  const [issueType, setIssueType] = useState<"RAW_ISSUE" | "PKG_ISSUE">("RAW_ISSUE");
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [returnQuantities, setReturnQuantities] = useState<Record<string, string>>({});
  const [returnKeys, setReturnKeys] = useState<Record<string, string>>({});
  const [returnNotes, setReturnNotes] = useState("");
  const [scrapQuantities, setScrapQuantities] = useState<Record<string, string>>({});
  const [scrapKeys, setScrapKeys] = useState<Record<string, string>>({});
  const [scrapReasons, setScrapReasons] = useState<Record<string, string>>({});
  const [scrapNotes, setScrapNotes] = useState("");
  const [consumptionLineId, setConsumptionLineId] = useState("");
  const [consumptionQuantity, setConsumptionQuantity] = useState("");
  const [consumptionNotes, setConsumptionNotes] = useState("");
  const [consumptionIdempotencyKey, setConsumptionIdempotencyKey] = useState("");

  const { data: reservations = [] } = useQuery<Reservation[]>({
    queryKey: ["mf-reservations", "issuable"],
    queryFn: () => mfApi.listReservations({ limit: "200" }),
    select: (rows) => rows.filter((reservation) =>
      ["ACTIVE", "PARTIALLY_ISSUED"].includes(reservation.status) &&
      reservation.lines.some((line) => outstanding(line) > 0)
    ),
  });
  const { data: rawTransactions = [] } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "issue"],
    queryFn: () => mfApi.listTransactions({ flow_type: "RAW_ISSUE", limit: "100" }),
  });
  const { data: packagingTransactions = [] } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "packaging-issue"],
    queryFn: () => mfApi.listTransactions({ flow_type: "PKG_ISSUE", limit: "100" }),
  });
  const transactions = [...rawTransactions, ...packagingTransactions].sort(
    (left, right) => new Date(right.transaction_datetime).getTime() - new Date(left.transaction_datetime).getTime()
  );
  const packageIssueLines = packagingTransactions
    .filter((transaction) => transaction.status === "POSTED")
    .flatMap((transaction) =>
      (transaction.lines || [])
        .filter((line) => line.issue_flag && line.item_type.trim().toLowerCase() === "material")
        .map((line) => ({ transaction, line }))
    );
  const selectedConsumption = packageIssueLines.find(({ line }) => line.id === consumptionLineId);
  const { data: orderConsumptions = [] } = useQuery<Consumption[]>({
    queryKey: ["mf-consumptions", selectedConsumption?.transaction.production_order_id],
    queryFn: () => mfApi.listConsumptions(selectedConsumption!.transaction.production_order_id!),
    enabled: Boolean(selectedConsumption?.transaction.production_order_id),
  });
  const settledConsumption = selectedConsumption
    ? orderConsumptions
        .filter((event) => event.flow_line_id === selectedConsumption.line.id)
        .reduce((total, event) => total + Number(event.quantity_consumed) + Number(event.quantity_returned) + Number(event.quantity_scrapped), 0)
    : 0;
  const outstandingConsumption = selectedConsumption
    ? Math.max(0, Number(selectedConsumption.line.quantity) - settledConsumption)
    : 0;
  const { data: returnTransactions = [] } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "material-returns"],
    queryFn: () => mfApi.listTransactions({ flow_type: "RETURN", limit: "100" }),
    select: (rows) => rows.filter((transaction) => transaction.source_document_type === "MATERIAL_ISSUE_LINE"),
  });
  const { data: scrapTransactions = [] } = useQuery<FlowTransaction[]>({
    queryKey: ["mf-transactions", "material-scrap"],
    queryFn: () => mfApi.listTransactions({ flow_type: "SCRAP", limit: "100" }),
    select: (rows) => rows.filter((transaction) => transaction.source_document_type === "MATERIAL_ISSUE_LINE"),
  });

  const selectedReservation = reservations.find((reservation) => reservation.id === reservationId);
  const selectedLines = useMemo(
    () => selectedReservation?.lines.filter((line) => outstanding(line) > 0) ?? [],
    [selectedReservation]
  );
  const requestLines = selectedLines.flatMap((line) => {
    const quantity = Number(quantities[line.id] || 0);
    return Number.isFinite(quantity) && quantity > 0
      ? [{ reservation_line_id: line.id, quantity }]
      : [];
  });

  const issue = useMutation({
    mutationFn: () => {
      if (!selectedReservation || requestLines.length === 0) {
        throw new Error("Select a reservation line and enter a positive issue quantity.");
      }
      const key = idempotencyKey || window.crypto.randomUUID();
      if (!idempotencyKey) setIdempotencyKey(key);
      const payload = {
        idempotency_key: key,
        notes: notes || undefined,
        lines: requestLines,
      };
      return issueType === "PKG_ISSUE"
        ? mfApi.issueReservedPackaging(selectedReservation.id, payload)
        : mfApi.issueReservedMaterials(selectedReservation.id, payload);
    },
    onSuccess: (transaction) => {
      setSuccessMessage(`Material issue ${transaction.flow_no} was posted.`);
      setErrorMessage("");
      setReservationId("");
      setQuantities({});
      setNotes("");
      setIdempotencyKey("");
      qc.invalidateQueries({ queryKey: ["mf-reservations"] });
      qc.invalidateQueries({ queryKey: ["mf-transactions"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
    },
    onError: () => {
      setErrorMessage("The issue was not confirmed. Check the reservation status, outstanding quantity, lot quality, and warehouse access. Retrying the same request reuses its safety key.");
    },
  });
  const recordPackagingConsumption = useMutation({
    mutationFn: () => {
      if (!selectedConsumption || !selectedConsumption.transaction.production_order_id) {
        throw new Error("Select a posted packaging issue line.");
      }
      const key = consumptionIdempotencyKey || window.crypto.randomUUID();
      if (!consumptionIdempotencyKey) setConsumptionIdempotencyKey(key);
      return mfApi.recordConsumption({
        production_order_id: selectedConsumption.transaction.production_order_id,
        flow_line_id: selectedConsumption.line.id,
        idempotency_key: key,
        quantity_consumed: Number(consumptionQuantity),
        notes: consumptionNotes || undefined,
      });
    },
    onSuccess: () => {
      setConsumptionQuantity("");
      setConsumptionNotes("");
      setConsumptionIdempotencyKey("");
      setSuccessMessage("Packaging consumption was linked to the production order.");
      setErrorMessage("");
      qc.invalidateQueries({ queryKey: ["mf-consumptions"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
    },
    onError: () => {
      setErrorMessage("Packaging consumption was not recorded. Check the issue line, order state, remaining quantity, and warehouse access.");
    },
  });
  const returnMaterial = useMutation({
    mutationFn: ({ issueLineId, quantity }: { issueLineId: string; quantity: number }) => {
      const key = returnKeys[issueLineId] || window.crypto.randomUUID();
      if (!returnKeys[issueLineId]) {
        setReturnKeys((current) => ({ ...current, [issueLineId]: key }));
      }
      return mfApi.returnExcessMaterial(issueLineId, {
        idempotency_key: key,
        quantity,
        notes: returnNotes || undefined,
      });
    },
    onSuccess: (transaction, variables) => {
      setSuccessMessage(`Excess material return ${transaction.flow_no} was posted and blocked pending review.`);
      setErrorMessage("");
      setReturnQuantities((current) => ({ ...current, [variables.issueLineId]: "" }));
      setReturnKeys((current) => {
        const next = { ...current };
        delete next[variables.issueLineId];
        return next;
      });
      setReturnNotes("");
      qc.invalidateQueries({ queryKey: ["mf-transactions"] });
      qc.invalidateQueries({ queryKey: ["mf-consumptions"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
    },
    onError: () => {
      setErrorMessage("The return was not posted. Check that the quantity is unused, the original issue is valid, and you have access to its warehouse. Retrying reuses the same safety key.");
    },
  });
  const scrapMaterial = useMutation({
    mutationFn: ({ issueLineId, quantity, reasonCode }: { issueLineId: string; quantity: number; reasonCode: "SPILLAGE" | "CONTAMINATION" | "DAMAGE" | "PROCESS_LOSS" | "OTHER" }) => {
      const key = scrapKeys[issueLineId] || window.crypto.randomUUID();
      if (!scrapKeys[issueLineId]) {
        setScrapKeys((current) => ({ ...current, [issueLineId]: key }));
      }
      return mfApi.scrapIssuedMaterial(issueLineId, {
        idempotency_key: key,
        quantity,
        reason_code: reasonCode,
        notes: scrapNotes.trim(),
      });
    },
    onSuccess: (transaction, variables) => {
      setSuccessMessage(`Scrap event ${transaction.flow_no} was recorded against the issued material; warehouse stock was not deducted a second time.`);
      setErrorMessage("");
      setScrapQuantities((current) => ({ ...current, [variables.issueLineId]: "" }));
      setScrapKeys((current) => {
        const next = { ...current };
        delete next[variables.issueLineId];
        return next;
      });
      setScrapNotes("");
      qc.invalidateQueries({ queryKey: ["mf-transactions"] });
      qc.invalidateQueries({ queryKey: ["mf-consumptions"] });
      qc.invalidateQueries({ queryKey: ["mf-dashboard"] });
    },
    onError: () => {
      setErrorMessage("The scrap/spillage record was not posted. Check remaining issued quantity, order state, and warehouse access. Retrying reuses the same safety key.");
    },
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Issue Reserved Materials</h1>
      </div>

      {successMessage && <div role="status" className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">{successMessage}</div>}
      {errorMessage && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{errorMessage}</div>}

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <div>
          <h2 className="font-semibold text-gray-800">New material issue</h2>
          <p className="mt-1 text-xs text-gray-500">Only material already reserved for a released production order can be issued. Stock and reservation balances post together.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-xs font-medium text-gray-600">
            Issue category
            <select
              value={issueType}
              onChange={(event) => { setIssueType(event.target.value as "RAW_ISSUE" | "PKG_ISSUE"); setQuantities({}); setIdempotencyKey(""); }}
              className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
            >
              <option value="RAW_ISSUE">Raw material</option>
              <option value="PKG_ISSUE">Packaging material</option>
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">
            Reservation
            <select
              value={reservationId}
              onChange={(event) => {
                setReservationId(event.target.value);
                setQuantities({});
                setIdempotencyKey("");
                setErrorMessage("");
              }}
              className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
            >
              <option value="">Select an active reservation</option>
              {reservations.map((reservation) => (
                <option key={reservation.id} value={reservation.id}>
                  {reservation.reservation_no} · {reservation.status}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">
            Notes
            <input
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
              placeholder="Optional issue note"
            />
          </label>
        </div>

        {selectedReservation && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs text-gray-600">
                <tr>
                  <th className="px-3 py-2">Material</th>
                  <th className="px-3 py-2">Lot</th>
                  <th className="px-3 py-2 text-right">Outstanding</th>
                  <th className="px-3 py-2">UOM</th>
                  <th className="px-3 py-2">Issue quantity</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {selectedLines.map((line) => (
                  <tr key={line.id}>
                    <td className="px-3 py-2">
                      <div>{line.material_name || line.material_id || "Material"}</div>
                      <div className="font-mono text-[11px] text-gray-500">Line {line.line_no}</div>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{line.lot_number || "Untracked lot"}</td>
                    <td className="px-3 py-2 text-right">{outstanding(line).toLocaleString()}</td>
                    <td className="px-3 py-2 text-xs">{line.uom}</td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        min="0"
                        max={outstanding(line)}
                        step="0.001"
                        value={quantities[line.id] || ""}
                        onChange={(event) => setQuantities((current) => ({ ...current, [line.id]: event.target.value }))}
                        className="w-32 rounded border px-2 py-1 text-right text-sm"
                        aria-label={`Issue quantity for reservation line ${line.line_no}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex justify-end">
          <button
            onClick={() => { setSuccessMessage(""); setErrorMessage(""); issue.mutate(); }}
            disabled={!selectedReservation || requestLines.length === 0 || issue.isPending}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {issue.isPending ? "Posting…" : issueType === "PKG_ISSUE" ? "Post packaging issue" : "Post raw-material issue"}
          </button>
        </div>
      </section>

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <div>
          <h2 className="font-semibold text-gray-900">Record actual packaging consumption</h2>
          <p className="mt-1 text-xs text-gray-500">Consumption links to a posted packaging issue and production order. The actual quantity is added to finished-lot genealogy when the order completes.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-xs font-medium text-gray-600">
            Posted packaging issue line
            <select
              value={consumptionLineId}
              onChange={(event) => { setConsumptionLineId(event.target.value); setConsumptionQuantity(""); setConsumptionIdempotencyKey(""); }}
              className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
            >
              <option value="">Select a packaging issue line</option>
              {packageIssueLines.map(({ transaction, line }) => (
                <option key={line.id} value={line.id}>
                  {transaction.flow_no} · {line.material_name || line.material_id} · {line.lot_number || "untracked lot"}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">
            Actual consumed quantity
            <input
              type="number"
              min="0"
              max={outstandingConsumption}
              step="0.001"
              value={consumptionQuantity}
              onChange={(event) => { setConsumptionQuantity(event.target.value); setConsumptionIdempotencyKey(""); }}
              className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
              disabled={!selectedConsumption}
            />
            {selectedConsumption && <span className="mt-1 block text-[11px]">Up to {outstandingConsumption.toLocaleString()} {selectedConsumption.line.uom} remains unsettled.</span>}
          </label>
        </div>
        <label className="block text-xs font-medium text-gray-600">
          Consumption note
          <input value={consumptionNotes} onChange={(event) => { setConsumptionNotes(event.target.value); setConsumptionIdempotencyKey(""); }} className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900" />
        </label>
        <button
          onClick={() => recordPackagingConsumption.mutate()}
          disabled={!selectedConsumption || Number(consumptionQuantity) <= 0 || Number(consumptionQuantity) > outstandingConsumption || recordPackagingConsumption.isPending}
          className="rounded-lg bg-violet-600 px-5 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-50"
        >
          {recordPackagingConsumption.isPending ? "Recording…" : "Record packaging consumption"}
        </button>
      </section>

      <section className="overflow-hidden rounded-lg border bg-white">
        <div className="border-b px-4 py-3">
          <h2 className="font-semibold text-gray-900">Recent material issues</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-600">
              <tr>
                {["Flow No", "Reservation", "Date", "Status", "Lines"].map((heading) => <th key={heading} className="px-4 py-2">{heading}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y">
              {transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="px-4 py-2 font-mono text-xs">{transaction.flow_no}</td>
                  <td className="px-4 py-2 font-mono text-xs">{transaction.source_document_id?.slice(0, 8) || "—"}</td>
                  <td className="px-4 py-2 text-xs">{new Date(transaction.transaction_datetime).toLocaleString()}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${FLOW_STATUS_COLORS[transaction.status] || ""}`}>{transaction.status}</span>
                  </td>
                  <td className="px-4 py-2 text-xs">{transaction.lines?.length || 0}</td>
                </tr>
              ))}
              {transactions.length === 0 && <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-gray-500">No material issue transactions yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <div>
          <h2 className="font-semibold text-gray-900">Return unused material</h2>
          <p className="mt-1 text-xs text-gray-500">Returns are linked to a posted issue line. Returned stock is recorded at its original location and blocked until review; it is not immediately available for another reservation.</p>
        </div>
        <label className="block max-w-xl text-xs font-medium text-gray-600">
          Return note
          <input
            value={returnNotes}
            onChange={(event) => setReturnNotes(event.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
            placeholder="Optional reason or condition note"
          />
        </label>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-600">
              <tr>
                {['Issue', 'Issue line', 'Material', 'Lot', 'Issued', 'Return quantity', 'Action'].map((heading) => <th key={heading} className="px-3 py-2">{heading}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y">
              {transactions.flatMap((transaction) => (transaction.lines || []).map((line) => (
                <tr key={line.id}>
                  <td className="px-3 py-2 font-mono text-xs">{transaction.flow_no}</td>
                  <td className="px-3 py-2 font-mono text-xs">{line.line_no}</td>
                  <td className="px-3 py-2">{line.material_name || line.material_id || "Material"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{line.lot_number || "Untracked"}</td>
                  <td className="px-3 py-2 text-right">{Number(line.quantity).toLocaleString()} {line.uom}</td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      max={line.quantity}
                      step="0.001"
                      value={returnQuantities[line.id] || ""}
                      onChange={(event) => setReturnQuantities((current) => ({ ...current, [line.id]: event.target.value }))}
                      className="w-32 rounded border px-2 py-1 text-right text-sm"
                      aria-label={`Return quantity for issue line ${line.line_no}`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => {
                        setSuccessMessage("");
                        setErrorMessage("");
                        returnMaterial.mutate({ issueLineId: line.id, quantity: Number(returnQuantities[line.id]) });
                      }}
                      disabled={!Number.isFinite(Number(returnQuantities[line.id])) || Number(returnQuantities[line.id]) <= 0 || returnMaterial.isPending}
                      className="rounded bg-amber-600 px-3 py-1.5 text-xs text-white hover:bg-amber-700 disabled:opacity-50"
                    >
                      {returnMaterial.isPending ? "Posting…" : "Post return"}
                    </button>
                  </td>
                </tr>
              ))) }
              {transactions.length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-center text-sm text-gray-500">No posted material issue lines are available for return.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="border-t pt-3">
          <h3 className="mb-2 text-sm font-semibold text-gray-800">Recent returns</h3>
          <div className="space-y-1 text-xs text-gray-600">
            {returnTransactions.slice(0, 10).map((transaction) => (
              <div key={transaction.id} className="flex flex-wrap gap-x-3 gap-y-1">
                <span className="font-mono">{transaction.flow_no}</span>
                <span>Issue {transaction.source_document_id?.slice(0, 8) || "—"}</span>
                <span>{transaction.lines?.reduce((sum, line) => sum + Number(line.quantity), 0).toLocaleString()} returned</span>
                <span>{new Date(transaction.transaction_datetime).toLocaleString()}</span>
              </div>
            ))}
            {returnTransactions.length === 0 && <p>No material returns recorded yet.</p>}
          </div>
        </div>
      </section>

      <section className="space-y-4 rounded-lg border bg-white p-5">
        <div>
          <h2 className="font-semibold text-gray-900">Record scrap or spillage</h2>
          <p className="mt-1 text-xs text-gray-500">Record a reason and quantity against a posted issue line. This records production loss; warehouse stock was already reduced when the material was issued.</p>
        </div>
        <label className="block max-w-xl text-xs font-medium text-gray-600">
          Explanation
          <input
            value={scrapNotes}
            onChange={(event) => setScrapNotes(event.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 text-sm font-normal text-gray-900"
            placeholder="Describe what was lost or damaged"
          />
        </label>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs text-gray-600">
              <tr>
                {['Issue', 'Line', 'Material', 'Issued', 'Reason', 'Scrap quantity', 'Action'].map((heading) => <th key={heading} className="px-3 py-2">{heading}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y">
              {transactions.flatMap((transaction) => (transaction.lines || []).map((line) => (
                <tr key={line.id}>
                  <td className="px-3 py-2 font-mono text-xs">{transaction.flow_no}</td>
                  <td className="px-3 py-2 font-mono text-xs">{line.line_no}</td>
                  <td className="px-3 py-2">{line.material_name || line.material_id || "Material"}</td>
                  <td className="px-3 py-2 text-right">{Number(line.quantity).toLocaleString()} {line.uom}</td>
                  <td className="px-3 py-2">
                    <select
                      value={scrapReasons[line.id] || ""}
                      onChange={(event) => setScrapReasons((current) => ({ ...current, [line.id]: event.target.value }))}
                      className="rounded border px-2 py-1 text-xs"
                      aria-label={`Scrap reason for issue line ${line.line_no}`}
                    >
                      <option value="">Select reason</option>
                      {[["SPILLAGE", "Spillage"], ["CONTAMINATION", "Contamination"], ["DAMAGE", "Damage"], ["PROCESS_LOSS", "Process loss"], ["OTHER", "Other"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min="0"
                      max={line.quantity}
                      step="0.001"
                      value={scrapQuantities[line.id] || ""}
                      onChange={(event) => setScrapQuantities((current) => ({ ...current, [line.id]: event.target.value }))}
                      className="w-32 rounded border px-2 py-1 text-right text-sm"
                      aria-label={`Scrap quantity for issue line ${line.line_no}`}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <button
                      onClick={() => {
                        setSuccessMessage("");
                        setErrorMessage("");
                        scrapMaterial.mutate({ issueLineId: line.id, quantity: Number(scrapQuantities[line.id]), reasonCode: scrapReasons[line.id] as "SPILLAGE" | "CONTAMINATION" | "DAMAGE" | "PROCESS_LOSS" | "OTHER" });
                      }}
                      disabled={!Number.isFinite(Number(scrapQuantities[line.id])) || Number(scrapQuantities[line.id]) <= 0 || !scrapReasons[line.id] || !scrapNotes.trim() || scrapMaterial.isPending}
                      className="rounded bg-red-600 px-3 py-1.5 text-xs text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      {scrapMaterial.isPending ? "Posting…" : "Record scrap"}
                    </button>
                  </td>
                </tr>
              ))) }
              {transactions.length === 0 && <tr><td colSpan={7} className="px-4 py-6 text-center text-sm text-gray-500">No posted material issue lines are available.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="border-t pt-3">
          <h3 className="mb-2 text-sm font-semibold text-gray-800">Recent scrap/spillage events</h3>
          <div className="space-y-1 text-xs text-gray-600">
            {scrapTransactions.slice(0, 10).map((transaction) => (
              <div key={transaction.id} className="flex flex-wrap gap-x-3 gap-y-1">
                <span className="font-mono">{transaction.flow_no}</span>
                <span>Issue {transaction.source_document_id?.slice(0, 8) || "—"}</span>
                <span>{transaction.lines?.reduce((sum, line) => sum + Number(line.quantity), 0).toLocaleString()} scrapped</span>
                <span>{transaction.notes || "No notes"}</span>
                <span>{new Date(transaction.transaction_datetime).toLocaleString()}</span>
              </div>
            ))}
            {scrapTransactions.length === 0 && <p>No scrap/spillage events recorded yet.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
