"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { advProductionApi } from "@/lib/productionAdvanced";

const modules = [
  { href:"/dashboard/production/work-centers",  icon:"🏭", title:"Work Centers",         desc:"Define machines, lines, and capacities" },
  { href:"/dashboard/production/routing",       icon:"🔀", title:"Routing",               desc:"Step-by-step production flow per product" },
  { href:"/dashboard/production/work-orders",   icon:"📋", title:"Work Orders",           desc:"Executable operations from production orders" },
  { href:"/dashboard/production/scheduling",    icon:"📅", title:"Scheduling",            desc:"Machine scheduling with conflict detection" },
  { href:"/dashboard/production/shifts",        icon:"⏱️", title:"Shifts",                desc:"Shift definitions and management" },
  { href:"/dashboard/production/time-tracking", icon:"⏲️", title:"Time Tracking",         desc:"Actual vs planned production time" },
  { href:"/dashboard/production/downtime",      icon:"⚠️", title:"Downtime Tracking",    desc:"Machine downtime events and categorization" },
  { href:"/dashboard/production/quality-control",icon:"🔬", title:"Quality Control",     desc:"Inline and final QC checks" },
  { href:"/dashboard/production/waste-yield",   icon:"♻️", title:"Waste & Yield",        desc:"Expected vs actual consumption and loss" },
  { href:"/dashboard/production/batch-lots",    icon:"🔖", title:"Batch / Lot Tracking", desc:"Full traceability and expiry tracking" },
  { href:"/dashboard/production/labor",         icon:"👷", title:"Labor Tracking",       desc:"Operator-level work logging" },
  { href:"/dashboard/production/oee",           icon:"📊", title:"OEE Tracking",         desc:"Availability, Performance, Quality metrics" },
];

export default function AdvancedProductionHub() {
  const { data: insights } = useQuery({ queryKey:["ai-insights"], queryFn:()=>advProductionApi.aiInsights() });
  const { data: oeeRecs   = [] } = useQuery({ queryKey:["oee"],   queryFn:()=>advProductionApi.listOEE({ date_from: new Date(Date.now()-7*86400000).toISOString().slice(0,10) }) });

  const lowOEE = oeeRecs.filter(r=>r.is_low_oee).length;
  const aiCount = insights?.total_insights ?? 0;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Advanced Production</h1>
        <p className="text-sm text-gray-500 mt-1">Full factory-level operational control — 11 modules</p>
      </div>

      {/* KPI bar */}
      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
          <p className="text-xs text-indigo-500 mb-1">AI Insights (active)</p>
          <p className="text-2xl font-bold text-indigo-700">{aiCount}</p>
          <p className="text-xs text-indigo-400 mt-0.5">anomalies & recommendations</p>
        </div>
        <div className={`rounded-xl border p-4 ${lowOEE>0?"border-red-200 bg-red-50":"border-green-100 bg-green-50"}`}>
          <p className={`text-xs mb-1 ${lowOEE>0?"text-red-500":"text-green-500"}`}>Low OEE Machines (7 days)</p>
          <p className={`text-2xl font-bold ${lowOEE>0?"text-red-700":"text-green-700"}`}>{lowOEE}</p>
          <p className={`text-xs mt-0.5 ${lowOEE>0?"text-red-400":"text-green-400"}`}>{lowOEE>0?"below 65% target":"all machines healthy"}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
          <p className="text-xs text-gray-500 mb-1">OEE Records (7 days)</p>
          <p className="text-2xl font-bold text-gray-700">{oeeRecs.length}</p>
          <p className="text-xs text-gray-400 mt-0.5">data points collected</p>
        </div>
      </div>

      {aiCount > 0 && insights && (
        <div className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h2 className="text-sm font-semibold text-amber-900 mb-2">Active AI Alerts</h2>
          <div className="space-y-1">
            {insights.insights.slice(0,4).map((ins,i)=>(
              <div key={i} className="flex gap-3 text-xs">
                <span className={`font-semibold ${ins.severity==="HIGH"?"text-red-600":ins.severity==="MEDIUM"?"text-yellow-600":"text-blue-600"}`}>[{ins.severity}]</span>
                <span className="text-amber-800">{ins.type.replace(/_/g," ")} — {ins.recommendation}</span>
              </div>
            ))}
            {insights.insights.length>4 && <p className="text-xs text-amber-600">+{insights.insights.length-4} more — view OEE module</p>}
          </div>
        </div>
      )}

      {/* Module Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {modules.map(m=>(
          <Link key={m.href} href={m.href} className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-indigo-300 hover:shadow-md transition-all">
            <div className="text-2xl mb-2">{m.icon}</div>
            <h3 className="text-sm font-semibold text-gray-900 group-hover:text-indigo-700">{m.title}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{m.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
