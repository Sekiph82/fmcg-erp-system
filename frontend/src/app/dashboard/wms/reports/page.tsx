"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { wmsApi, NearExpiryRow, LowStockRow, StockAgingRow, LotTraceResult } from "@/lib/wms";
import { warehousesApi } from "@/lib/warehouses";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

type Tab = "near-expiry" | "low-stock" | "aging" | "lot-trace" | "ledger";

const TABS: { key: Tab; label: string }[] = [
  { key: "near-expiry", label: "Near Expiry" },
  { key: "low-stock", label: "Low Stock" },
  { key: "aging", label: "Stock Aging" },
  { key: "lot-trace", label: "Lot Traceability" },
  { key: "ledger", label: "Movement Ledger" },
];

const MOVEMENT_TYPES = [
  { value: "", label: "All Types" },
  { value: "RECEIPT", label: "Receipt" },
  { value: "ISSUE", label: "Issue" },
  { value: "TRANSFER", label: "Transfer" },
  { value: "ADJUSTMENT", label: "Adjustment" },
  { value: "RETURN", label: "Return" },
];

const AGE_BUCKET_VARIANT = (bucket: string) =>
  bucket === "0-30 days" ? "green"
  : bucket === "31-60 days" ? "blue"
  : bucket === "61-90 days" ? "blue"
  : "red";

export default function WMSReportsPage() {
  const [tab, setTab] = useState<Tab>("near-expiry");
  const [warehouseId, setWarehouseId] = useState("");
  const [daysAhead, setDaysAhead] = useState("30");
  const [lotNumber, setLotNumber] = useState("");
  const [lotSearch, setLotSearch] = useState("");
  const [ledgerDateFrom, setLedgerDateFrom] = useState("");
  const [ledgerDateTo, setLedgerDateTo] = useState("");
  const [ledgerType, setLedgerType] = useState("");

  const { data: warehouses = [] } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(0, 100),
  });

  const whOpts = [{ value: "", label: "All Warehouses" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))];

  const { data: nearExpiry = [], isFetching: loadingNearExpiry } = useQuery({
    queryKey: ["wms-near-expiry", daysAhead, warehouseId],
    queryFn: () => wmsApi.nearExpiryReport(Number(daysAhead) || 30, warehouseId || undefined),
    enabled: tab === "near-expiry",
  });

  const { data: lowStock = [], isFetching: loadingLowStock } = useQuery({
    queryKey: ["wms-low-stock", warehouseId],
    queryFn: () => wmsApi.lowStockReport(warehouseId || undefined),
    enabled: tab === "low-stock",
  });

  const { data: aging = [], isFetching: loadingAging } = useQuery({
    queryKey: ["wms-aging", warehouseId],
    queryFn: () => wmsApi.agingReport(warehouseId || undefined),
    enabled: tab === "aging",
  });

  const { data: lotTrace, isFetching: loadingTrace } = useQuery<LotTraceResult>({
    queryKey: ["wms-lot-trace", lotSearch],
    queryFn: () => wmsApi.lotTrace(lotSearch),
    enabled: !!lotSearch,
    retry: false,
  });

  const { data: ledger = [], isFetching: loadingLedger } = useQuery({
    queryKey: ["wms-ledger", warehouseId, ledgerDateFrom, ledgerDateTo, ledgerType],
    queryFn: () =>
      wmsApi.movementLedger({
        warehouse_id: warehouseId || undefined,
        date_from: ledgerDateFrom || undefined,
        date_to: ledgerDateTo || undefined,
        movement_type: ledgerType || undefined,
        limit: 500,
      }),
    enabled: tab === "ledger",
  });

  const Spinner = () => (
    <div className="flex justify-center py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">WMS Reports</h1>
        <p className="text-sm text-gray-500 mt-1">Inventory intelligence — expiry, stock levels, aging, traceability</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1 mb-6 w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Shared warehouse filter (all tabs except lot-trace) */}
      {tab !== "lot-trace" && (
        <div className="mb-4 flex items-center gap-3 flex-wrap">
          <Select
            options={whOpts}
            value={warehouseId}
            onChange={(e) => setWarehouseId(e.target.value)}
            className="w-52"
          />
          {tab === "near-expiry" && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Days ahead:</span>
              <Input
                type="number"
                value={daysAhead}
                onChange={(e) => setDaysAhead(e.target.value)}
                className="w-24"
              />
            </div>
          )}
          {tab === "ledger" && (
            <>
              <Input
                type="date"
                value={ledgerDateFrom}
                onChange={(e) => setLedgerDateFrom(e.target.value)}
                className="w-40"
              />
              <span className="text-sm text-gray-400">to</span>
              <Input
                type="date"
                value={ledgerDateTo}
                onChange={(e) => setLedgerDateTo(e.target.value)}
                className="w-40"
              />
              <Select
                options={MOVEMENT_TYPES}
                value={ledgerType}
                onChange={(e) => setLedgerType(e.target.value)}
                className="w-44"
              />
            </>
          )}
        </div>
      )}

      {/* ── Near Expiry ── */}
      {tab === "near-expiry" && (
        loadingNearExpiry ? <Spinner /> :
        <>
          <div className="mb-3 text-sm text-gray-500">{nearExpiry.length} item(s) expiring within {daysAhead} days</div>
          <Table
            keyField="lot_number"
            data={nearExpiry}
            emptyMessage="No items near expiry."
            columns={[
              {
                header: "Item",
                accessor: (r) => (
                  <span>
                    {r.product_sku && <span className="font-mono text-xs text-gray-400 mr-1">{r.product_sku}</span>}
                    {r.product_name || r.material_name || "—"}
                  </span>
                ),
              },
              { header: "Lot", accessor: (r) => <span className="font-mono text-xs">{r.lot_number}</span> },
              { header: "Warehouse", accessor: "warehouse_name" },
              {
                header: "Expiry Date",
                accessor: (r) => (
                  <span className={r.is_expired ? "text-red-600 font-semibold" : Number(r.days_to_expiry) <= 7 ? "text-amber-600 font-medium" : "text-gray-700"}>
                    {new Date(r.expiry_date).toLocaleDateString()}
                  </span>
                ),
              },
              {
                header: "Days Left",
                accessor: (r) => (
                  <Badge
                    label={r.is_expired ? "EXPIRED" : `${r.days_to_expiry}d`}
                    variant={r.is_expired ? "red" : Number(r.days_to_expiry) <= 7 ? "red" : Number(r.days_to_expiry) <= 30 ? "blue" : "green"}
                  />
                ),
              },
              {
                header: "Qty Available",
                accessor: (r) => (
                  <span className={r.quantity_available <= 0 ? "text-gray-400" : ""}>
                    {Number(r.quantity_available).toFixed(3)}
                  </span>
                ),
              },
            ]}
          />
        </>
      )}

      {/* ── Low Stock ── */}
      {tab === "low-stock" && (
        loadingLowStock ? <Spinner /> :
        <>
          <div className="mb-3 text-sm text-gray-500">{lowStock.length} product(s) below reorder point</div>
          <Table
            keyField={(r) => `${r.product_id}-${r.warehouse_name}`}
            data={lowStock}
            emptyMessage="All stock levels are above reorder points."
            columns={[
              {
                header: "Product",
                accessor: (r) => (
                  <span>
                    {r.product_sku && <span className="font-mono text-xs text-gray-400 mr-1">{r.product_sku}</span>}
                    {r.product_name || "—"}
                  </span>
                ),
              },
              { header: "Warehouse", accessor: "warehouse_name" },
              { header: "Available", accessor: (r) => <span className="text-red-600 font-semibold">{Number(r.quantity_available).toFixed(3)}</span> },
              { header: "Reorder Point", accessor: (r) => Number(r.reorder_point).toFixed(3) },
              {
                header: "Shortage",
                accessor: (r) => (
                  <span className="text-red-600 font-bold">
                    -{Math.abs(Number(r.shortage)).toFixed(3)}
                  </span>
                ),
              },
            ]}
          />
        </>
      )}

      {/* ── Stock Aging ── */}
      {tab === "aging" && (
        loadingAging ? <Spinner /> :
        <>
          <div className="mb-3 text-sm text-gray-500">{aging.length} stock row(s)</div>
          <Table
            keyField={(r) => `${r.lot_number}-${r.warehouse_name}`}
            data={aging}
            emptyMessage="No stock aging data."
            columns={[
              {
                header: "Item",
                accessor: (r) => (
                  <span>
                    {r.product_sku && <span className="font-mono text-xs text-gray-400 mr-1">{r.product_sku}</span>}
                    {r.product_name || "—"}
                  </span>
                ),
              },
              { header: "Lot", accessor: (r) => r.lot_number ? <span className="font-mono text-xs">{r.lot_number}</span> : "—" },
              { header: "Warehouse", accessor: "warehouse_name" },
              { header: "Qty on Hand", accessor: (r) => Number(r.quantity_on_hand).toFixed(3) },
              {
                header: "Age",
                accessor: (r) => (
                  <div className="flex items-center gap-2">
                    <Badge label={r.age_bucket} variant={AGE_BUCKET_VARIANT(r.age_bucket)} />
                    {r.age_days != null && <span className="text-xs text-gray-400">{r.age_days}d</span>}
                  </div>
                ),
              },
              { header: "First Received", accessor: (r) => r.first_received_date ? new Date(r.first_received_date).toLocaleDateString() : "—" },
              {
                header: "Status",
                accessor: (r) => r.is_blocked
                  ? <Badge label="Blocked" variant="red" />
                  : <Badge label="OK" variant="green" />,
              },
            ]}
          />
        </>
      )}

      {/* ── Lot Traceability ── */}
      {tab === "lot-trace" && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Input
              placeholder="Enter lot number…"
              value={lotNumber}
              onChange={(e) => setLotNumber(e.target.value)}
              className="w-72"
              onKeyDown={(e) => { if (e.key === "Enter" && lotNumber.trim()) setLotSearch(lotNumber.trim()); }}
            />
            <Button
              onClick={() => setLotSearch(lotNumber.trim())}
              disabled={!lotNumber.trim()}
              loading={loadingTrace}
            >
              Trace
            </Button>
          </div>

          {lotTrace && (
            <div className="space-y-4">
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between flex-wrap gap-4">
                  <div>
                    <p className="text-xs text-gray-400 mb-1">Lot Number</p>
                    <p className="font-mono text-lg font-bold">{lotTrace.lot_number}</p>
                    {(lotTrace.product_name || lotTrace.material_name) && (
                      <p className="text-sm text-gray-500 mt-1">
                        {lotTrace.product_sku && <span className="mr-1 text-gray-400">{lotTrace.product_sku}</span>}
                        {lotTrace.product_name || lotTrace.material_name}
                      </p>
                    )}
                  </div>
                  <div className="text-right text-sm text-gray-500 space-y-1">
                    {lotTrace.manufacture_date && (
                      <p>Manufactured: {new Date(lotTrace.manufacture_date).toLocaleDateString()}</p>
                    )}
                    {lotTrace.expiry_date && (
                      <p>Expires: {new Date(lotTrace.expiry_date).toLocaleDateString()}</p>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-base font-semibold text-gray-800 mb-3">Trace Events ({lotTrace.events.length})</h3>
                <div className="space-y-2">
                  {lotTrace.events.map((ev, i) => (
                    <div key={i} className="flex items-start gap-4 rounded-lg border border-gray-100 bg-white px-4 py-3 shadow-sm">
                      <div className="mt-0.5">
                        <Badge
                          label={ev.event_type}
                          variant={
                            ev.event_type === "RECEIPT" ? "green"
                            : ev.event_type === "ISSUE" ? "blue"
                            : ev.event_type === "ADJUSTMENT" ? "blue"
                            : "red"
                          }
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800">{ev.description}</p>
                        {ev.order_no && <p className="text-xs text-gray-500 mt-0.5">Ref: {ev.order_no}</p>}
                        {ev.warehouse_name && <p className="text-xs text-gray-500">Warehouse: {ev.warehouse_name}</p>}
                      </div>
                      <div className="text-right shrink-0">
                        <p className={`text-sm font-semibold ${ev.quantity > 0 ? "text-green-600" : "text-red-500"}`}>
                          {ev.quantity > 0 ? "+" : ""}{Number(ev.quantity).toFixed(3)}
                        </p>
                        <p className="text-xs text-gray-400">{new Date(ev.event_date).toLocaleDateString()}</p>
                      </div>
                    </div>
                  ))}
                  {lotTrace.events.length === 0 && (
                    <p className="text-sm text-gray-500 text-center py-8">No trace events found for this lot.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {!lotTrace && !loadingTrace && lotSearch && (
            <div className="text-center py-12 text-gray-500 text-sm">Lot not found: {lotSearch}</div>
          )}
        </div>
      )}

      {/* ── Movement Ledger ── */}
      {tab === "ledger" && (
        loadingLedger ? <Spinner /> :
        <>
          <div className="mb-3 text-sm text-gray-500">{ledger.length} movement(s)</div>
          <Table
            keyField="id"
            data={ledger}
            emptyMessage="No movements found for the selected filters."
            columns={[
              { header: "Reference", accessor: (r) => <span className="font-mono text-xs font-medium">{r.reference_number}</span> },
              {
                header: "Type",
                accessor: (r) => (
                  <Badge
                    label={r.movement_type}
                    variant={
                      r.movement_type === "RECEIPT" ? "green"
                      : r.movement_type === "ISSUE" ? "blue"
                      : r.movement_type === "ADJUSTMENT" ? "blue"
                      : "red"
                    }
                  />
                ),
              },
              {
                header: "Item",
                accessor: (r) => (
                  <span>
                    {r.product_sku && <span className="font-mono text-xs text-gray-400 mr-1">{r.product_sku}</span>}
                    {r.product_name || "—"}
                  </span>
                ),
              },
              { header: "Lot", accessor: (r) => r.lot_number ? <span className="font-mono text-xs">{r.lot_number}</span> : "—" },
              {
                header: "Flow",
                accessor: (r) => (
                  <span className="text-xs text-gray-500">
                    {r.source_warehouse && <span>{r.source_warehouse}</span>}
                    {r.source_warehouse && r.destination_warehouse && <span className="mx-1">→</span>}
                    {r.destination_warehouse && <span>{r.destination_warehouse}</span>}
                  </span>
                ),
              },
              {
                header: "Qty",
                accessor: (r) => (
                  <span className="font-semibold">{Number(r.quantity).toFixed(3)}</span>
                ),
              },
              {
                header: "Cost",
                accessor: (r) => r.total_cost != null
                  ? <span className="text-gray-700">{Number(r.total_cost).toFixed(2)}</span>
                  : "—",
              },
              { header: "Date", accessor: (r) => new Date(r.movement_date).toLocaleDateString() },
              { header: "By", accessor: (r) => r.created_by ?? "—" },
            ]}
          />
        </>
      )}
    </div>
  );
}
