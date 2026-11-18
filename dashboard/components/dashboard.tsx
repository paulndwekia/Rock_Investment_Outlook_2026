"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity, BarChart3, BookOpen, ChevronDown, Database, Landmark,
  LayoutDashboard, Menu, RefreshCw, ShieldCheck, X, Globe2, Clock3
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";
import type { OverviewResponse } from "@/lib/types";

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Equity research", icon: BarChart3 },
  { label: "Fixed income", icon: Landmark },
  { label: "Macro indicators", icon: Globe2 },
  { label: "Risk analysis", icon: Activity },
  { label: "Research notes", icon: BookOpen },
  { label: "Data & sources", icon: Database }
];

const sectionCopy: Record<string, { kicker: string; title: string; body: string; topics: string[]; note: string }> = {
  "Equity research": {
    kicker: "Nairobi Securities Exchange",
    title: "Equity research",
    body: "Examine listed-security performance and market activity through dated observations, company information and clearly defined calculations. Security-level comparisons should use consistent periods and disclose gaps in the underlying data.",
    topics: [
      "Security price and trading history",
      "Turnover and market activity",
      "Market breadth and concentration",
      "Company fundamentals and valuation",
      "Foreign investor flows"
    ],
    note: "Historical price, volume and flow data must be checked for corporate actions, missing sessions, currency units and source permissions before it is used in comparative analysis."
  },
  "Fixed income": {
    kicker: "Rates and government securities",
    title: "Fixed income research",
    body: "Follow the Kenyan government securities market, from Treasury-bill auction outcomes to bond yields and the shape of the yield curve. Keep observed market quotations separate from derived measures and model estimates.",
    topics: [
      "Treasury-bill auction results",
      "Government bond yields and prices",
      "Yield curve and term structure",
      "Auction performance and issuance",
      "Duration, convexity and interest-rate risk"
    ],
    note: "Yield observations must retain their tenor, quotation convention, observation date and source. Do not combine auction rates, secondary-market yields and modelled curve points as though they were the same measure."
  },
  "Macro indicators": {
    kicker: "Kenyan economic conditions",
    title: "Macroeconomic indicators",
    body: "Bring together published indicators that help explain the operating environment for Kenyan assets. Each series should carry its reporting period, publication date, unit and originating institution.",
    topics: [
      "Inflation and consumer prices",
      "Exchange rates",
      "Liquidity and monetary conditions",
      "Purchasing Managers’ Index",
      "Foreign-exchange reserves and fuel prices"
    ],
    note: "Economic indicators are not always published at the same frequency. Comparisons should use the correct reference period and disclose revisions, lags and differences in definitions."
  },
  "Risk analysis": {
    kicker: "Measurement and uncertainty",
    title: "Market risk analysis",
    body: "Assess historical risk and test how conclusions change under clearly stated assumptions. Risk measures describe observed or modelled behaviour; they are not promises about future outcomes.",
    topics: [
      "Historical volatility and drawdowns",
      "Correlation and co-movement",
      "Liquidity and concentration",
      "Scenario assumptions and sensitivity",
      "Data quality and model limitations"
    ],
    note: "Every risk statistic should identify its sample period, frequency, return convention and methodology. Forward-looking scenarios must be labelled as conditional analysis rather than forecasts."
  },
  "Research notes": {
    kicker: "Research record",
    title: "Research notes",
    body: "Keep the investment thesis, supporting evidence, analytical choices and subsequent revisions together. Notes should make it possible for another researcher to understand how a conclusion was reached.",
    topics: [
      "Kenya Investment Outlook 2026",
      "Research Challenge methodology",
      "Investment themes and catalysts",
      "Assumptions and limitations",
      "Research updates and revisions"
    ],
    note: "The research record should distinguish sourced facts, calculations, interpretation and scenario assumptions. Update a conclusion when its supporting evidence changes, and retain the date and reason for the revision."
  },
  "Data & sources": {
    kicker: "Provenance and permissions",
    title: "Data and sources",
    body: "A reliable research dashboard needs more than a chart. It needs a record of where each observation came from, when it was recorded, how it was transformed and whether it may be displayed.",
    topics: [
      "Source register and licence status",
      "Observation dates and import times",
      "Dataset validation and audit trail",
      "Definitions, units and transformations",
      "Approved exports and attribution"
    ],
    note: "Rock Data Plus integration remains subject to Rock Investment Bank’s written approval and the applicable data terms. Until an authorised API or export arrangement is confirmed, do not automate access or republish restricted source records."
  }
};

function dateLabel(value?: string | null) {
  if (!value) return "Not available";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Not available" : parsed.toLocaleString("en-KE", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
  });
}

function StatusPill({ status }: { status: OverviewResponse["status"] }) {
  const styles = status === "ok"
    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
    : "bg-amber-50 text-amber-900 border-amber-200";
  const label = status === "ok" ? "Data service connected" : status === "unavailable" ? "Data service unavailable" : "Awaiting approved data feed";
  return <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${styles}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{label}</span>;
}

function MetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return <div className="rounded-xl border border-[#E7E3DA] bg-white p-4 shadow-soft">
    <p className="text-xs font-semibold uppercase tracking-[.12em] text-[#7B817F]">{label}</p>
    <p className="mt-3 text-[25px] font-semibold tracking-tight text-[#17212A]">{value}</p>
    <p className="mt-1 text-xs leading-5 text-[#808783]">{hint}</p>
  </div>;
}

export default function Dashboard() {
  const [data, setData] = useState<OverviewResponse>({ status: "not_configured" });
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [active, setActive] = useState("Overview");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/overview", { cache: "no-store" });
      const payload = await response.json() as OverviewResponse;
      setData(payload);
    } catch {
      setData({ status: "unavailable", message: "The dashboard could not retrieve its data status." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const chartData = useMemo(() => (data.market_series ?? []).map((point) => ({
    date: new Date(point.observed_at).toLocaleDateString("en-KE", { day: "2-digit", month: "short" }),
    dataset: point.dataset,
    series: point.series,
    value: point.value,
    source: point.source_name,
    unit: point.unit
  })), [data.market_series]);

  const latestUpdate = dateLabel(data.latest_observation);
  const connected = data.status === "ok";

  return <div className="min-h-screen bg-[#F5F4F0]">
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-[258px] flex-col border-r border-[#E7E3DA] bg-[#FBFAF7] transition-transform duration-200 lg:translate-x-0 ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="flex h-[82px] items-center justify-between border-b border-[#EAE6DE] px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#17212A] text-[#D5B66F]"><Landmark size={17} /></span>
            <span className="text-[15px] font-semibold tracking-tight text-[#17212A]">Kenya Investment</span>
          </div>
          <p className="ml-10 mt-0.5 text-[10px] uppercase tracking-[.2em] text-[#8A8E89]">Intelligence</p>
        </div>
        <button onClick={() => setMenuOpen(false)} className="rounded-lg p-2 text-[#6F7775] hover:bg-[#F0EEE8] lg:hidden" aria-label="Close navigation"><X size={18} /></button>
      </div>

      <div className="px-4 pt-7">
        <p className="px-3 text-[10px] font-semibold uppercase tracking-[.18em] text-[#9A9C96]">Research workspace</p>
        <nav className="mt-3 space-y-1">
          {navigation.map(({ label, icon: Icon }) => {
            const selected = active === label;
            return <button key={label} onClick={() => { setActive(label); setMenuOpen(false); }} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] transition-colors ${selected ? "bg-[#EEE7D8] font-semibold text-[#5B4828]" : "text-[#636D6B] hover:bg-[#F1EFE9] hover:text-[#202B31]"}`}>
              <Icon size={16} strokeWidth={1.8} />{label}
              {selected && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[#B89552]" />}
            </button>;
          })}
        </nav>
      </div>

      <div className="mt-auto border-t border-[#EAE6DE] p-5">
        <div className="rounded-xl bg-[#F0EEE8] p-3">
          <div className="flex items-center gap-2 text-[#716044]"><ShieldCheck size={15} /><span className="text-xs font-semibold">Research integrity</span></div>
          <p className="mt-2 text-[11px] leading-5 text-[#747A76]">Observed data, calculations and scenarios are kept separate.</p>
        </div>
        <p className="mt-4 text-[10px] leading-4 text-[#9A9C96]">Independent research platform<br />Kenya · © {new Date().getFullYear()}</p>
      </div>
    </aside>

    {menuOpen && <button className="fixed inset-0 z-30 bg-[#101820]/30 lg:hidden" aria-label="Close menu overlay" onClick={() => setMenuOpen(false)} />}

    <main className="min-h-screen lg:pl-[258px]">
      <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-[#E7E3DA] bg-[#F5F4F0]/95 px-5 backdrop-blur md:px-9">
        <div className="flex items-center gap-3">
          <button onClick={() => setMenuOpen(true)} className="rounded-lg p-2 text-[#45504F] hover:bg-white lg:hidden" aria-label="Open navigation"><Menu size={19} /></button>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[.19em] text-[#9B8A66]">Kenya markets / Research terminal</p>
            <p className="mt-0.5 text-sm font-semibold text-[#29343B]">{active}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill status={data.status} />
          <button onClick={() => void refresh()} disabled={loading} className="flex h-9 items-center gap-2 rounded-lg border border-[#E0DDD5] bg-white px-3 text-xs font-medium text-[#56615E] transition hover:border-[#C5AA73] disabled:opacity-50">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /><span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-[1450px] px-5 py-8 md:px-9 md:py-10">
        <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .35 }} className="relative overflow-hidden rounded-2xl bg-[#17212A] px-6 py-8 text-white shadow-soft md:px-9 md:py-9">
          <div className="pointer-events-none absolute -right-10 -top-28 h-80 w-80 rounded-full border border-[#C7A968]/20" />
          <div className="pointer-events-none absolute -right-2 -top-20 h-64 w-64 rounded-full border border-[#C7A968]/15" />
          <div className="relative max-w-3xl">
            <p className="text-[10px] font-semibold uppercase tracking-[.24em] text-[#D7BC83]">Market research · Kenya</p>
            <h1 className="mt-4 max-w-2xl text-[30px] font-semibold leading-[1.15] tracking-tight md:text-[38px]">A clearer view of the Kenyan investment market.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-[#C1C8C8]">Equities, fixed income, macroeconomic indicators and market risk in one research workspace. Every figure should be traceable to its source and observation date.</p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-md border border-[#C7A968]/35 bg-[#C7A968]/10 px-3 py-2 text-[11px] font-medium text-[#E9D7AC]"><Activity size={13} />Research workspace</span>
              <span className="text-[11px] text-[#AAB4B2]">Built around the Kenya Investment Outlook research</span>
            </div>
          </div>
        </motion.section>

        {active === "Overview" ? (<>\n        <section className="mt-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[.16em] text-[#9A8A68]">The market at a glance</p>
            <h2 className="mt-1.5 text-xl font-semibold tracking-tight text-[#1B252D]">Research snapshot</h2>
            <p className="mt-1 text-xs text-[#858B86]">Only verified observations are shown. No placeholder prices or generated returns.</p>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-[#858B86]"><Clock3 size={13} />Latest observation: {latestUpdate}</div>
        </section>

        <section className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Recorded observations" value={connected ? (data.total_observations ?? 0).toLocaleString("en-KE") : "—"} hint={connected ? "Validated records in the research store" : "Shown when a verified data feed is connected"} />
          <MetricCard label="Datasets available" value={connected ? String(data.dataset_count ?? 0) : "—"} hint="Equities, rates and macro series where authorised" />
          <MetricCard label="Latest observation" value={connected && data.latest_observation ? new Date(data.latest_observation).toLocaleDateString("en-KE", { day: "2-digit", month: "short", year: "numeric" }) : "—"} hint="Observation date, not the import date" />
          <MetricCard label="Data service" value={connected ? "Connected" : "Not connected"} hint={connected ? "Read-only research feed" : "Waiting for approved source access"} />
        </section>

        <section className="mt-6 grid gap-4 xl:grid-cols-[1.7fr_1fr]">
          <div className="rounded-xl border border-[#E7E3DA] bg-white p-5 shadow-soft md:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[.16em] text-[#A08A5D]">Historical observations</p>
                <h3 className="mt-1 text-base font-semibold text-[#263139]">Market series</h3>
                <p className="mt-1 text-xs text-[#858B86]">The chart will plot imported observations, not illustrative values.</p>
              </div>
              <span className="rounded-md bg-[#F4F0E7] px-2.5 py-1.5 text-[10px] font-medium text-[#7D6942]">Source-linked</span>
            </div>
            <div className="mt-5 h-[260px]">
              {chartData.length > 1 ? <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <defs><linearGradient id="marketGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#B89552" stopOpacity={0.22} /><stop offset="95%" stopColor="#B89552" stopOpacity={0.01} /></linearGradient></defs>
                  <CartesianGrid vertical={false} stroke="#EEECE6" />
                  <XAxis dataKey="date" tick={{ fill: "#858B86", fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={24} />
                  <YAxis tick={{ fill: "#858B86", fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ border: "1px solid #E7E3DA", borderRadius: 10, fontSize: 12 }} formatter={(value) => [Number(value).toLocaleString("en-KE"), "Observed value"]} />
                  <Area type="monotone" dataKey="value" stroke="#A9894B" strokeWidth={2} fill="url(#marketGold)" connectNulls={false} />
                </AreaChart>
              </ResponsiveContainer> : <div className="flex h-full flex-col items-center justify-center rounded-lg border border-dashed border-[#E5E1D8] bg-[#FAF9F6] px-6 text-center">
                <BarChart3 size={22} className="text-[#B89552]" strokeWidth={1.5} />
                <p className="mt-3 text-sm font-medium text-[#49534F]">No verified series connected yet</p>
                <p className="mt-1 max-w-sm text-xs leading-5 text-[#8A908B]">When an authorised dataset is ingested, its actual observations and dates will appear here.</p>
              </div>}
            </div>
            {chartData.length > 0 && <p className="mt-2 text-[10px] leading-5 text-[#90958F]">Series: {chartData[chartData.length - 1]?.series} · Dataset: {chartData[chartData.length - 1]?.dataset} · Unit: {chartData[chartData.length - 1]?.unit ?? "not specified"} · Source: {chartData[chartData.length - 1]?.source}</p>}
          </div>

          <div className="rounded-xl border border-[#E7E3DA] bg-white p-5 shadow-soft md:p-6">
            <p className="text-[10px] font-semibold uppercase tracking-[.16em] text-[#A08A5D]">Data coverage</p>
            <h3 className="mt-1 text-base font-semibold text-[#263139]">What is connected</h3>
            <p className="mt-1 text-xs leading-5 text-[#858B86]">A source should appear here only after its records pass validation.</p>
            <div className="mt-5 space-y-3">
              {(data.datasets ?? []).length ? data.datasets?.map((item) => <div key={item.dataset} className="flex items-start justify-between gap-3 border-b border-[#F0EEE8] pb-3">
                <div><p className="text-sm font-medium text-[#37423F]">{item.dataset}</p><p className="mt-1 text-[10px] text-[#929891]">{item.source_name ?? "Source not labelled"}</p></div>
                <div className="text-right"><p className="text-sm font-semibold text-[#36413D]">{item.observations.toLocaleString("en-KE")}</p><p className="mt-1 text-[10px] text-[#929891]">{dateLabel(item.last_observed_at)}</p></div>
              </div>) : <div className="rounded-lg bg-[#F8F7F3] px-4 py-5">
                <div className="flex items-center gap-2 text-[#7F6940]"><Database size={16} /><p className="text-xs font-semibold">No datasets published</p></div>
                <p className="mt-2 text-xs leading-5 text-[#858B86]">The platform is ready for authorised Rock Data Plus exports or another approved source feed.</p>
              </div>}
            </div>
          </div>
        </section>

        {data.status !== "ok" && <section className="mt-5 rounded-xl border border-[#E8DCC0] bg-[#FBF8F0] p-4 md:p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-[#F0E6CF] p-2 text-[#856C3D]"><Database size={17} /></div>
            <div>
              <p className="text-sm font-semibold text-[#4C412C]">The dashboard is built; the verified data connection is still pending.</p>
              <p className="mt-1 max-w-4xl text-xs leading-6 text-[#746B5B]">{data.message ?? "Connect the authorised data service to publish actual observations."} The current display intentionally contains no invented prices, market performance or macroeconomic readings.</p>
            </div>
          </div>
        </section>}

        <section className="mt-7 grid gap-4 md:grid-cols-3">
          {[
            { title: "Equities", body: "Security-level history, trading activity, returns and market breadth.", icon: BarChart3 },
            { title: "Fixed income", body: "Treasury bill rates, bond yields, auction records and curve structure.", icon: Landmark },
            { title: "Macroeconomy", body: "Inflation, exchange rates, liquidity and other published indicators.", icon: Globe2 }
          ].map(({ title, body, icon: Icon }) => <button key={title} onClick={() => setActive(title === "Equities" ? "Equity research" : title === "Fixed income" ? "Fixed income" : "Macro indicators")} className="group rounded-xl border border-[#E7E3DA] bg-white p-5 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-[#CFBB91]">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#F1EBDD] text-[#8A7040]"><Icon size={17} /></div>
            <h3 className="mt-4 text-sm font-semibold text-[#29343B]">{title}</h3>
            <p className="mt-1.5 text-xs leading-5 text-[#828A85]">{body}</p>
            <span className="mt-4 inline-flex items-center gap-1 text-[11px] font-semibold text-[#8A7040]">Explore research <ChevronDown size={13} className="-rotate-90 transition group-hover:translate-x-0.5" /></span>
          </button>)}
        </section>

        </>) : (
          <section className="mt-8 space-y-5">
            {(() => { const content = sectionCopy[active]; return <>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[.16em] text-[#9A8A68]">{content.kicker}</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#1B252D]">{content.title}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-[#68726E]">{content.body}</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {content.topics.map((topic, index) => <div key={topic} className="rounded-xl border border-[#E7E3DA] bg-white p-5 shadow-soft">
                  <p className="text-[10px] font-semibold uppercase tracking-[.16em] text-[#A08A5D]">Research area</p>
                  <h3 className="mt-2 text-sm font-semibold text-[#29343B]">{topic}</h3>
                  <p className="mt-2 text-xs leading-5 text-[#858B86]">Observations and analytical outputs will appear here once the authorised source data is available.</p>
                </div>)}
              </div>
              <div className="rounded-xl border border-[#E8DCC0] bg-[#FBF8F0] p-5">
                <p className="text-sm font-semibold text-[#4C412C]">A note on the data</p>
                <p className="mt-2 text-xs leading-6 text-[#746B5B]">{content.note}</p>
                <p className="mt-3 text-[11px] text-[#887A61]">Current feed status: {connected ? "connected" : "awaiting verified source connection"}.</p>
              </div>
            </>; })()}
          </section>
        )}
        <footer className="mt-10 flex flex-col justify-between gap-3 border-t border-[#E3DFD6] pt-5 text-[10px] leading-5 text-[#929791] sm:flex-row">
          <p>Kenya Investment Intelligence · Independent research platform</p>
          <div className="flex gap-4"><a href="/terms" className="hover:text-[#5D503A]">Terms of use</a><a href="/privacy" className="hover:text-[#5D503A]">Privacy</a><a href="https://github.com/paulndwekia/Rock_Investment_Outlook_2026" target="_blank" rel="noreferrer" className="hover:text-[#5D503A]">Project repository</a></div>
        </footer>
      </div>
    </main>
  </div>;
}