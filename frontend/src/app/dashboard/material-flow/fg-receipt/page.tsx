"use client";

export default function FGReceiptPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">← Dashboard</a>
        <h1 className="text-xl font-bold text-gray-900">Finished Goods Receipt</h1>
      </div>

      <section className="max-w-3xl rounded-lg border border-blue-200 bg-blue-50 p-5 text-sm text-blue-900">
        <h2 className="font-semibold">Receive finished goods from a production order</h2>
        <p className="mt-2">
          Complete an in-progress production order to post its finished-goods lot and stock movement. If the order has recorded WIP, the receipt must match the available WIP quantity and consumes its stage/location balances in the same transaction.
        </p>
        <p className="mt-2">
          Production completion also records the existing finished-goods receipt, quality inspection, and genealogy records. Direct receipt drafts are disabled so inventory and WIP cannot drift apart.
        </p>
        <a
          href="/dashboard/production/orders"
          className="mt-4 inline-flex rounded bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700"
        >
          Open production orders
        </a>
      </section>
    </div>
  );
}
