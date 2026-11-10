"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FlowStage, WIPBalance, mfApi } from "@/lib/materialFlow";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default function WIPTransferPage() {
  const queryClient = useQueryClient();
  const [orderId, setOrderId] = useState("");
  const [outputQuantity, setOutputQuantity] = useState("");
  const [outputUom, setOutputUom] = useState("KG");
  const [outputStageId, setOutputStageId] = useState("");
  const [selectedBalanceKey, setSelectedBalanceKey] = useState("");
  const [selectedBalanceKeys, setSelectedBalanceKeys] = useState<string[]>([]);
  const [transferQuantity, setTransferQuantity] = useState("");
  const [destinationStageId, setDestinationStageId] = useState("");
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState("");
  const validOrderId = UUID_RE.test(orderId.trim());

  const { data: stages = [] } = useQuery<FlowStage[]>({
    queryKey: ["mf-stages"],
    queryFn: () => mfApi.listStages(),
  });
  const { data: balances = [], isFetching } = useQuery<WIPBalance[]>({
    queryKey: ["mf-wip-balances", orderId],
    queryFn: () => mfApi.listWipBalances(orderId.trim()),
    enabled: validOrderId,
  });
  const outputStage = stages.find((stage) => stage.id === outputStageId);
  const selectedBalance = balances.find((balance) =>
    `${balance.origin_line_id}:${balance.stage_id}:${balance.location_id}` === selectedBalanceKey
  );
  const selectedBalances = balances.filter((balance) =>
    selectedBalanceKeys.includes(`${balance.origin_line_id}:${balance.stage_id}:${balance.location_id}`)
  );
  const destinationStage = stages.find((stage) => stage.id === destinationStageId);
  const usableStages = stages.filter((stage) => stage.active_flag && stage.location_id);

  const refreshWip = async () => {
    await queryClient.invalidateQueries({ queryKey: ["mf-wip-balances", orderId] });
    await queryClient.invalidateQueries({ queryKey: ["mf-transactions"] });
  };
  const output = useMutation({
    mutationFn: () => mfApi.recordWipOutput({
      idempotency_key: crypto.randomUUID(),
      production_order_id: orderId.trim(),
      quantity: Number(outputQuantity),
      uom: outputUom.trim().toUpperCase(),
      destination_stage_id: outputStageId,
      destination_location_id: outputStage?.location_id || "",
      notes: notes.trim() || undefined,
    }),
    onSuccess: async (transaction) => {
      setMessage(`WIP output ${transaction.flow_no} recorded.`);
      setOutputQuantity("");
      await refreshWip();
    },
  });
  const transfer = useMutation({
    mutationFn: () => {
      if (!selectedBalance || !destinationStage?.location_id) throw new Error("Select an available WIP balance and a configured destination stage.");
      return mfApi.transferWip(orderId.trim(), selectedBalance.origin_line_id, {
        idempotency_key: crypto.randomUUID(),
        quantity: Number(transferQuantity),
        source_stage_id: selectedBalance.stage_id,
        source_location_id: selectedBalance.location_id,
        destination_stage_id: destinationStage.id,
        destination_location_id: destinationStage.location_id,
        notes: notes.trim() || undefined,
      });
    },
    onSuccess: async (transaction) => {
      setMessage(`WIP transfer ${transaction.flow_no} posted.`);
      setTransferQuantity("");
      await refreshWip();
    },
  });
  const bulkTransfer = useMutation({
    mutationFn: () => {
      if (!selectedBalances.length || !destinationStage?.location_id) throw new Error("Select WIP balances and a configured destination stage.");
      return mfApi.transferWipBulk(orderId.trim(), {
        idempotency_key: crypto.randomUUID(),
        lines: selectedBalances.map((balance) => ({
          origin_line_id: balance.origin_line_id,
          quantity: balance.quantity,
          source_stage_id: balance.stage_id,
          source_location_id: balance.location_id,
          destination_stage_id: destinationStage.id,
          destination_location_id: destinationStage.location_id || "",
        })),
        notes: notes.trim() || undefined,
      });
    },
    onSuccess: async (transaction) => {
      setMessage(`Bulk WIP transfer ${transaction.flow_no} posted (${transaction.lines.length} lines).`);
      setSelectedBalanceKeys([]);
      await refreshWip();
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">WIP Output & Stage Transfer</h1>
      </div>

      {message && <div role="status" className="bg-green-50 border border-green-200 text-green-700 p-3 rounded-lg text-sm">{message}</div>}
      {(output.error || transfer.error || bulkTransfer.error) && (
        <div role="alert" className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm">
          {(output.error || transfer.error || bulkTransfer.error)?.message || "WIP request failed."}
        </div>
      )}

      <section className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Production order</h2>
        <label className="block text-xs font-medium text-gray-600">
          Production Order ID
          <input value={orderId} onChange={(event) => { setOrderId(event.target.value); setSelectedBalanceKey(""); setSelectedBalanceKeys([]); }} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal" placeholder="UUID" />
        </label>
      </section>

      <section className="bg-white rounded-lg border p-5 space-y-4">
        <div>
          <h2 className="font-semibold text-gray-800">Record measured WIP output</h2>
          <p className="text-xs text-gray-500 mt-1">Uses the order product and batch. Quantity is capped at the order plan; no warehouse stock is created.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="text-xs font-medium text-gray-600">Quantity
            <input type="number" min="0.001" step="0.001" value={outputQuantity} onChange={(event) => setOutputQuantity(event.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal" />
          </label>
          <label className="text-xs font-medium text-gray-600">Order UOM
            <input value={outputUom} onChange={(event) => setOutputUom(event.target.value)} maxLength={20} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal" />
          </label>
          <label className="text-xs font-medium text-gray-600">Destination stage
            <select value={outputStageId} onChange={(event) => setOutputStageId(event.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal">
              <option value="">Select a configured stage</option>
              {usableStages.map((stage) => <option key={stage.id} value={stage.id}>{stage.stage_name}</option>)}
            </select>
          </label>
        </div>
        <button onClick={() => output.mutate()} disabled={!validOrderId || !outputQuantity || !outputStage?.location_id || output.isPending} className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm disabled:opacity-50">
          {output.isPending ? "Recording…" : "Record WIP output"}
        </button>
      </section>

      <section className="bg-white rounded-lg border p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold text-gray-800">Available WIP by stage and location</h2>
            <p className="text-xs text-gray-500 mt-1">Balances are derived from posted output and transfer history.</p>
          </div>
          {isFetching && <span className="text-xs text-gray-500">Refreshing…</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
          <thead className="bg-gray-50"><tr>{["Select", "Batch", "Stage", "Location", "Quality", "Available", "Transfer"].map((heading) => <th key={heading} className="px-3 py-2 text-left text-xs text-gray-600">{heading}</th>)}</tr></thead>
            <tbody className="divide-y">
              {balances.map((balance) => {
                const balanceKey = `${balance.origin_line_id}:${balance.stage_id}:${balance.location_id}`;
                return <tr key={balanceKey}>
                <td className="px-3 py-2"><input type="checkbox" aria-label={`Select ${balance.batch_id} at ${balance.location_code}`} checked={selectedBalanceKeys.includes(balanceKey)} onChange={(event) => setSelectedBalanceKeys((current) => event.target.checked ? [...current, balanceKey] : current.filter((key) => key !== balanceKey))} /></td>
                <td className="px-3 py-2 font-mono text-xs">{balance.batch_id}</td>
                <td className="px-3 py-2">{balance.stage_name}</td>
                <td className="px-3 py-2">{balance.location_code}</td>
                <td className="px-3 py-2">{balance.quality_status}</td>
                <td className="px-3 py-2">{balance.quantity} {balance.uom}</td>
                <td className="px-3 py-2"><button onClick={() => setSelectedBalanceKey(balanceKey)} className="text-indigo-700 underline">Select</button></td>
              </tr>})}
              {validOrderId && balances.length === 0 && !isFetching && <tr><td colSpan={7} className="px-3 py-6 text-center text-gray-500">No posted WIP output is recorded for this order.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-white rounded-lg border p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Move selected WIP</h2>
        <p className="text-xs text-gray-500">A transfer keeps the same batch, quality status, and quantity unit. The source balance is locked and checked before posting.</p>
        {selectedBalance && <p className="text-sm text-gray-700">Selected: {selectedBalance.batch_id} · {selectedBalance.quantity} {selectedBalance.uom} at {selectedBalance.stage_name} / {selectedBalance.location_code}</p>}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="text-xs font-medium text-gray-600">Transfer quantity
            <input type="number" min="0.001" step="0.001" max={selectedBalance?.quantity} value={transferQuantity} onChange={(event) => setTransferQuantity(event.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal" />
          </label>
          <label className="text-xs font-medium text-gray-600">Destination stage
            <select value={destinationStageId} onChange={(event) => setDestinationStageId(event.target.value)} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal">
              <option value="">Select a configured stage</option>
              {usableStages.filter((stage) => stage.id !== selectedBalance?.stage_id).map((stage) => <option key={stage.id} value={stage.id}>{stage.stage_name}</option>)}
            </select>
          </label>
          <label className="text-xs font-medium text-gray-600">Notes
            <input value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={1000} className="mt-1 w-full border rounded px-3 py-2 text-sm font-normal" />
          </label>
        </div>
        <button onClick={() => transfer.mutate()} disabled={!validOrderId || !selectedBalance || !destinationStage?.location_id || !transferQuantity || transfer.isPending} className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm disabled:opacity-50">
          {transfer.isPending ? "Posting…" : "Post WIP transfer"}
        </button>
        <button onClick={() => bulkTransfer.mutate()} disabled={!validOrderId || !selectedBalances.length || !destinationStage?.location_id || bulkTransfer.isPending} className="ml-2 bg-purple-700 text-white px-5 py-2 rounded-lg text-sm disabled:opacity-50">
          {bulkTransfer.isPending ? "Posting…" : `Bulk move selected full balances (${selectedBalances.length})`}
        </button>
      </section>
    </div>
  );
}
