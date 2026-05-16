"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { posApi, POSPaymentMethod, POSSaleLineCreate, fmtKES } from "@/lib/pos";
import { productsApi, Product } from "@/lib/products";
import { Button } from "@/components/ui/Button";

interface CartLine {
  product: Product;
  qty: number;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
}

// ── Cart helpers ──────────────────────────────────────────────────────────────

function lineTotal(l: CartLine) {
  return l.qty * l.unit_price * (1 - l.discount_pct / 100) * (1 + l.tax_rate / 100);
}

function cartTotals(cart: CartLine[]) {
  const subtotal = cart.reduce((s, l) => s + l.qty * l.unit_price, 0);
  const disc     = cart.reduce((s, l) => s + l.qty * l.unit_price * (l.discount_pct / 100), 0);
  const tax      = cart.reduce((s, l) => s + l.qty * l.unit_price * (1 - l.discount_pct / 100) * (l.tax_rate / 100), 0);
  return { subtotal, disc, tax, total: subtotal - disc + tax };
}

// ── Open session modal ────────────────────────────────────────────────────────

function OpenSessionModal({ onClose, onOpen }: { onClose: () => void; onOpen: () => void }) {
  const [float, setFloat] = useState("0");
  const [register, setRegister] = useState("REGISTER-1");
  const mut = useMutation({
    mutationFn: () => posApi.openSession(register, parseFloat(float) || 0),
    onSuccess: () => { onOpen(); onClose(); },
  });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-80 p-6 space-y-4">
        <h2 className="text-lg font-bold">Open Register</h2>
        <div>
          <label className="text-sm font-medium text-gray-700">Register ID</label>
          <input className="w-full border rounded px-3 py-2 text-sm mt-1" value={register}
            onChange={e => setRegister(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Opening Float (KES)</label>
          <input type="number" min={0} className="w-full border rounded px-3 py-2 text-sm mt-1" value={float}
            onChange={e => setFloat(e.target.value)} />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending}>
            {mut.isPending ? "Opening…" : "Open"}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Close session modal ───────────────────────────────────────────────────────

function CloseSessionModal({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [cash, setCash] = useState("0");
  const [notes, setNotes] = useState("");
  const mut = useMutation({
    mutationFn: () => posApi.closeSession(sessionId, parseFloat(cash) || 0, notes || undefined),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["pos-session"] }); onClose(); },
  });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-80 p-6 space-y-4">
        <h2 className="text-lg font-bold">Close Register</h2>
        <div>
          <label className="text-sm font-medium text-gray-700">Actual Cash in Drawer (KES)</label>
          <input type="number" min={0} step={0.01} className="w-full border rounded px-3 py-2 text-sm mt-1" value={cash}
            onChange={e => setCash(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Notes</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm mt-1" rows={2} value={notes}
            onChange={e => setNotes(e.target.value)} />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending} className="bg-red-600 hover:bg-red-700">
            {mut.isPending ? "Closing…" : "Close Register"}
          </Button>
        </div>
        {mut.isError && <p className="text-xs text-red-600">{(mut.error as Error).message}</p>}
      </div>
    </div>
  );
}

// ── Payment modal ─────────────────────────────────────────────────────────────

function PaymentModal({ total, onPay, onClose }: {
  total: number;
  onPay: (method: POSPaymentMethod, amountPaid: number, mpesaRef?: string) => void;
  onClose: () => void;
}) {
  const [method, setMethod] = useState<POSPaymentMethod>("CASH");
  const [amountPaid, setAmountPaid] = useState(String(Math.ceil(total)));
  const [mpesaRef, setMpesaRef] = useState("");

  const change = parseFloat(amountPaid) - total;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl w-80 p-6 space-y-4">
        <h2 className="text-lg font-bold">Payment</h2>
        <div className="text-center">
          <div className="text-xs text-gray-500">Amount Due</div>
          <div className="text-3xl font-bold text-gray-900">{fmtKES(total)}</div>
        </div>

        <div className="flex gap-2">
          {(["CASH", "MPESA", "CARD"] as POSPaymentMethod[]).map(m => (
            <button key={m} onClick={() => setMethod(m)}
              className={`flex-1 py-2 rounded text-sm font-medium border transition-colors ${method === m ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-200"}`}>
              {m}
            </button>
          ))}
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700">Amount Received</label>
          <input type="number" min={total} step={1} className="w-full border rounded px-3 py-2 text-sm mt-1 text-xl"
            value={amountPaid} onChange={e => setAmountPaid(e.target.value)} />
        </div>

        {method === "MPESA" && (
          <div>
            <label className="text-sm font-medium text-gray-700">M-Pesa Reference</label>
            <input className="w-full border rounded px-3 py-2 text-sm mt-1" value={mpesaRef}
              onChange={e => setMpesaRef(e.target.value)} placeholder="e.g. OGH12345KJ" />
          </div>
        )}

        {method === "CASH" && change >= 0 && (
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-xs text-green-600">Change</div>
            <div className="text-2xl font-bold text-green-700">{fmtKES(change)}</div>
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <button
            onClick={() => onPay(method, parseFloat(amountPaid) || total, mpesaRef || undefined)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700">
            Complete Sale
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main POS terminal ─────────────────────────────────────────────────────────

function POSTerminalTab() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<CartLine[]>([]);
  const [showOpenSession, setShowOpenSession] = useState(false);
  const [showCloseSession, setShowCloseSession] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [lastSale, setLastSale] = useState<{ no: string; total: number; change: number } | null>(null);

  const { data: session, refetch: refetchSession } = useQuery({
    queryKey: ["pos-session"],
    queryFn: posApi.currentSession,
  });

  const { data: allProducts = [] } = useQuery({
    queryKey: ["products-all"],
    queryFn: () => productsApi.list(),
  });

  const { data: dash, refetch: refetchDash } = useQuery({
    queryKey: ["pos-dashboard"],
    queryFn: posApi.dashboard,
  });

  const filtered = useMemo(() => {
    if (!search) return allProducts.slice(0, 40);
    const q = search.toLowerCase();
    return allProducts.filter(p =>
      p.name.toLowerCase().includes(q) || p.sku?.toLowerCase().includes(q)
    ).slice(0, 40);
  }, [allProducts, search]);

  const totals = cartTotals(cart);

  const addToCart = (product: Product) => {
    setCart(prev => {
      const existing = prev.find(l => l.product.id === product.id);
      if (existing) {
        return prev.map(l => l.product.id === product.id ? { ...l, qty: l.qty + 1 } : l);
      }
      return [...prev, {
        product,
        qty: 1,
        unit_price: product.selling_price ?? 0,
        discount_pct: 0,
        tax_rate: 16,
      }];
    });
  };

  const removeFromCart = (productId: string) =>
    setCart(prev => prev.filter(l => l.product.id !== productId));

  const updateQty = (productId: string, qty: number) => {
    if (qty <= 0) return removeFromCart(productId);
    setCart(prev => prev.map(l => l.product.id === productId ? { ...l, qty } : l));
  };

  const saleMut = useMutation({
    mutationFn: (args: { method: POSPaymentMethod; amountPaid: number; mpesaRef?: string }) =>
      posApi.createSale({
        payment_method: args.method,
        amount_paid: args.amountPaid,
        mpesa_ref: args.mpesaRef,
        lines: cart.map(l => ({
          product_id: l.product.id,
          qty: l.qty,
          unit_price: l.unit_price,
          discount_pct: l.discount_pct,
          tax_rate: l.tax_rate,
        })),
      }),
    onSuccess: (sale) => {
      setLastSale({ no: sale.sale_no, total: sale.sale_total, change: sale.change_given ?? 0 });
      setCart([]);
      setShowPayment(false);
      refetchSession();
      refetchDash();
    },
  });

  const handlePay = (method: POSPaymentMethod, amountPaid: number, mpesaRef?: string) => {
    saleMut.mutate({ method, amountPaid, mpesaRef });
  };

  const hasSession = session && session.status === "OPEN";

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Left: Product grid */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="bg-white border-b px-4 py-3 flex items-center gap-3">
          <h1 className="text-lg font-bold text-gray-900">Point of Sale</h1>
          {hasSession ? (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
              {session.register_id} — OPEN
            </span>
          ) : (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">NO OPEN SESSION</span>
          )}
          <div className="flex-1" />
          {dash && (
            <div className="text-xs text-gray-500">
              Today: <strong>{dash.today_sales_count} sales · {fmtKES(dash.today_sales_total)}</strong>
            </div>
          )}
          {hasSession ? (
            <button onClick={() => setShowCloseSession(true)}
              className="text-xs px-3 py-1.5 rounded bg-red-50 text-red-700 border border-red-200 hover:bg-red-100">
              Close Register
            </button>
          ) : (
            <button onClick={() => setShowOpenSession(true)}
              className="text-xs px-3 py-1.5 rounded bg-green-50 text-green-700 border border-green-200 hover:bg-green-100">
              Open Register
            </button>
          )}
        </div>

        {/* Search */}
        <div className="px-4 py-2 bg-white border-b">
          <input
            className="w-full border rounded-lg px-4 py-2.5 text-sm"
            placeholder="Search by product name or SKU…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            autoFocus
          />
        </div>

        {/* Product grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {!hasSession && (
            <div className="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
              Open a register session to start selling.
            </div>
          )}
          <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {filtered.map(p => (
              <button
                key={p.id}
                disabled={!hasSession}
                onClick={() => addToCart(p)}
                className="bg-white rounded-xl border p-3 text-left hover:shadow-md hover:border-blue-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
              >
                <div className="text-xs text-gray-400 font-mono">{p.sku}</div>
                <div className="text-sm font-semibold text-gray-900 mt-0.5 line-clamp-2">{p.name}</div>
                <div className="text-base font-bold text-blue-600 mt-1">
                  {p.selling_price != null ? fmtKES(p.selling_price) : "—"}
                </div>
              </button>
            ))}
            {filtered.length === 0 && (
              <div className="col-span-5 p-8 text-center text-gray-400">No products match your search.</div>
            )}
          </div>
        </div>
      </div>

      {/* Right: Cart */}
      <div className="w-80 bg-white border-l flex flex-col shadow-lg">
        <div className="px-4 py-3 border-b">
          <h2 className="font-bold text-gray-900">Cart ({cart.length} items)</h2>
        </div>

        {/* Receipt success */}
        {lastSale && (
          <div className="mx-3 mt-3 bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
            <div className="font-semibold text-green-700">Sale {lastSale.no} complete</div>
            <div className="text-green-600">Total: {fmtKES(lastSale.total)}</div>
            {lastSale.change > 0 && <div className="text-green-600">Change: {fmtKES(lastSale.change)}</div>}
            <button onClick={() => setLastSale(null)} className="text-xs text-green-500 mt-1 hover:underline">Dismiss</button>
          </div>
        )}

        {/* Cart items */}
        <div className="flex-1 overflow-y-auto py-2">
          {cart.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">Cart is empty. Tap products to add.</div>
          ) : cart.map(l => (
            <div key={l.product.id} className="px-4 py-2 border-b hover:bg-gray-50">
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{l.product.name}</div>
                  <div className="text-xs text-gray-400">{fmtKES(l.unit_price)} each</div>
                </div>
                <button onClick={() => removeFromCart(l.product.id)}
                  className="text-gray-300 hover:text-red-400 ml-2 text-lg leading-none">×</button>
              </div>
              <div className="flex items-center gap-2 mt-1.5">
                <button onClick={() => updateQty(l.product.id, l.qty - 1)}
                  className="w-7 h-7 rounded-full border text-gray-600 hover:bg-gray-100 font-bold flex items-center justify-center">−</button>
                <span className="text-sm font-semibold w-8 text-center">{l.qty}</span>
                <button onClick={() => updateQty(l.product.id, l.qty + 1)}
                  className="w-7 h-7 rounded-full border text-gray-600 hover:bg-gray-100 font-bold flex items-center justify-center">+</button>
                <span className="ml-auto text-sm font-bold text-gray-900">{fmtKES(lineTotal(l))}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Totals */}
        <div className="border-t px-4 py-3 space-y-1.5 text-sm">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span><span>{fmtKES(totals.subtotal)}</span>
          </div>
          {totals.disc > 0 && (
            <div className="flex justify-between text-gray-600">
              <span>Discount</span><span>-{fmtKES(totals.disc)}</span>
            </div>
          )}
          <div className="flex justify-between text-gray-600">
            <span>Tax (VAT)</span><span>{fmtKES(totals.tax)}</span>
          </div>
          <div className="flex justify-between font-bold text-lg text-gray-900 border-t pt-2">
            <span>Total</span><span>{fmtKES(totals.total)}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="px-4 pb-4 space-y-2">
          <button
            disabled={!hasSession || cart.length === 0 || saleMut.isPending}
            onClick={() => setShowPayment(true)}
            className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold text-base hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saleMut.isPending ? "Processing…" : "Pay Now"}
          </button>
          <button onClick={() => setCart([])} disabled={cart.length === 0}
            className="w-full py-2 bg-gray-100 text-gray-600 rounded-xl text-sm hover:bg-gray-200 disabled:opacity-40">
            Clear Cart
          </button>
          {saleMut.isError && (
            <p className="text-xs text-red-600 text-center">{(saleMut.error as Error).message}</p>
          )}
        </div>
      </div>

      {/* Modals */}
      {showOpenSession && (
        <OpenSessionModal onClose={() => setShowOpenSession(false)} onOpen={() => refetchSession()} />
      )}
      {showCloseSession && hasSession && (
        <CloseSessionModal sessionId={session.id} onClose={() => setShowCloseSession(false)} />
      )}
      {showPayment && (
        <PaymentModal total={totals.total} onPay={handlePay} onClose={() => setShowPayment(false)} />
      )}
    </div>
  );
}

const POSSalesPage    = dynamic(() => import("@/app/dashboard/pos/sales/page"),    { ssr: false });
const POSSessionsPage = dynamic(() => import("@/app/dashboard/pos/sessions/page"), { ssr: false });

export default function POSPage() {
  const tabs = [
    { key: "pos",      label: "POS Terminal", permission: "sales.view", content: <POSTerminalTab /> },
    { key: "sales",    label: "Sales",        permission: "sales.view", content: <POSSalesPage /> },
    { key: "sessions", label: "Sessions",     permission: "sales.view", content: <POSSessionsPage /> },
  ];
  return (
    <ModuleWorkspace
      title="POS"
      description="Point of sale terminal, daily sales, session management"
      permission="sales.view"
      tabs={tabs}
      defaultTab="pos"
    />
  );
}
