"use client";

import React, { useState, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

// Currency formatter for Indian Rupees
function formatINR(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || isNaN(amount)) return "₹0";
  if (amount >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Cr`;
  }
  if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} L`;
  }
  return `₹${amount.toLocaleString("en-IN")}`;
}

export default function LedgerLensApp() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "alerts" | "projects" | "mps" | "verification" | "inspector"
  >("overview");

  // Health and System status
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [dashboardSummary, setDashboardSummary] = useState<any>(null);
  const [riskDist, setRiskDist] = useState<any[]>([]);
  const [stateSummary, setStateSummary] = useState<any[]>([]);

  // Alerts data
  const [alerts, setAlerts] = useState<any[]>([]);
  const [alertFilter, setAlertFilter] = useState<string>("ALL");

  // Projects data
  const [projects, setProjects] = useState<any[]>([]);
  const [projectSearch, setProjectSearch] = useState<string>("");
  const [projectRiskFilter, setProjectRiskFilter] = useState<string>("ALL");
  const [selectedProject, setSelectedProject] = useState<any>(null);
  const [similarWorks, setSimilarWorks] = useState<any[]>([]);

  // MP Allocations data
  const [mpAllocations, setMpAllocations] = useState<any[]>([]);
  const [mpSearch, setMpSearch] = useState<string>("");
  const [mpOutlierOnly, setMpOutlierOnly] = useState<boolean>(false);

  // Verification Cases
  const [cases, setCases] = useState<any[]>([]);
  const [verificationFeedback, setVerificationFeedback] = useState<string | null>(null);

  // Inspector query
  const [inspectQuery, setInspectQuery] = useState<string>("MPLADS-MA-2025-0001");
  const [inspectResult, setInspectResult] = useState<any>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Load Dashboard Data
  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      // 1. Health
      const hRes = await fetch(`${API_BASE}/health`).catch(() => null);
      if (hRes && hRes.ok) setSystemHealth(await hRes.json());

      // 2. Summary
      const sRes = await fetch(`${API_BASE}/dashboard/summary`).catch(() => null);
      if (sRes && sRes.ok) setDashboardSummary(await sRes.json());

      // 3. Risk Distribution
      const rdRes = await fetch(`${API_BASE}/dashboard/risk-distribution`).catch(() => null);
      if (rdRes && rdRes.ok) setRiskDist(await rdRes.json());

      // 4. State Summary
      const ssRes = await fetch(`${API_BASE}/dashboard/state-summary?limit=10`).catch(() => null);
      if (ssRes && ssRes.ok) setStateSummary(await ssRes.json());

      // 5. Alerts
      const alRes = await fetch(`${API_BASE}/alerts?per_page=30`).catch(() => null);
      if (alRes && alRes.ok) {
        const d = await alRes.json();
        setAlerts(d.data || []);
      }

      // 6. Projects
      const pRes = await fetch(`${API_BASE}/projects?per_page=50`).catch(() => null);
      if (pRes && pRes.ok) {
        const pd = await pRes.json();
        setProjects(pd.data || []);
      }

      // 7. MP Allocations
      const mpRes = await fetch(`${API_BASE}/mp-allocations?per_page=50`).catch(() => null);
      if (mpRes && mpRes.ok) {
        const mpd = await mpRes.json();
        setMpAllocations(mpd.data || []);
      }

      // 8. Verification Cases
      const vcRes = await fetch(`${API_BASE}/verification?per_page=30`).catch(() => null);
      if (vcRes && vcRes.ok) {
        const vcd = await vcRes.json();
        setCases(vcd.data || []);
      }
    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 25000);
    return () => clearInterval(interval);
  }, []);

  // Inspect project detail
  const handleSelectProject = async (p: any) => {
    setSelectedProject(p);
    try {
      const res = await fetch(`${API_BASE}/projects/${p.project_id}`);
      if (res.ok) {
        const detail = await res.json();
        setSelectedProject({ ...p, ...detail });
      }
      const simRes = await fetch(`${API_BASE}/projects/${p.project_id}/similar`);
      if (simRes.ok) {
        const simData = await simRes.json();
        setSimilarWorks(simData.similar_projects || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Officer verification decision
  const handleVerificationDecision = async (
    caseId: string,
    decision: "VERIFIED" | "FALSE_SIGNAL" | "ACTION_REQUIRED" | "RESOLVED"
  ) => {
    try {
      const res = await fetch(`${API_BASE}/verification/${caseId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision,
          notes: `Decision recorded by Monitoring Officer: ${decision}`,
          actor: "Officer-In-Charge",
        }),
      });
      if (res.ok) {
        setVerificationFeedback(`Case ${caseId} updated to: ${decision}`);
        setTimeout(() => setVerificationFeedback(null), 4000);
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Run Inspector
  const handleInspectQuery = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects/${inspectQuery}`);
      if (res.ok) {
        const data = await res.json();
        setInspectResult(data);
      } else {
        setInspectResult({ error: `Record '${inspectQuery}' not found in active dataset.` });
      }
    } catch (e) {
      setInspectResult({ error: "Failed to connect to ML risk engine." });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-black">
      {/* ─── Top Government & Platform Banner ─── */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-white/20">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
                  Ledger Lens
                </h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  LIVE
                </span>
              </div>
              <p className="text-xs text-slate-400">
                AI-Powered MPLADS Risk Intelligence & Decision Support Platform
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="text-right hidden sm:block">
              <div className="text-[11px] font-medium text-slate-400">
                Data Layer: <span className="text-slate-200">Official eSAKSHI + Demo Synthesis</span>
              </div>
              <div className="text-[10px] text-slate-500">
                Backend: <span className="text-cyan-400">FastAPI 1.0.0</span> | DB: <span className="text-emerald-400">Active</span>
              </div>
            </div>

            <button
              onClick={fetchData}
              disabled={isRefreshing}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition flex items-center gap-1.5 shadow-sm active:scale-95"
            >
              <svg className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* ─── Tabs Navigation ─── */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 overflow-x-auto border-t border-slate-800/60 pt-1">
          {[
            { id: "overview", label: "Executive Overview", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" },
            { id: "alerts", label: "Risk Alerts", count: alerts.length, icon: "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" },
            { id: "projects", label: "Project Works", count: projects.length, icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" },
            { id: "mps", label: "MP Allocations", count: 543, icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" },
            { id: "verification", label: "Verification Desk", count: cases.length, icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
            { id: "inspector", label: "Explainable AI Inspector", icon: "M13 10V3L4 14h7v7l9-11h-7z" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 text-xs font-semibold rounded-t-lg transition flex items-center gap-2 border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-cyan-400 text-cyan-400 bg-slate-900/80"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40"
              }`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d={tab.icon} />
              </svg>
              {tab.label}
              {tab.count !== undefined && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeTab === tab.id ? "bg-cyan-500/20 text-cyan-300" : "bg-slate-800 text-slate-400"
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </header>

      {/* ─── Feedback Toast ─── */}
      {verificationFeedback && (
        <div className="fixed bottom-6 right-6 z-50 bg-emerald-950 border border-emerald-500/60 text-emerald-200 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 animate-fade-in">
          <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-xs font-semibold">{verificationFeedback}</span>
        </div>
      )}

      {/* ─── Main Content ─── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Core Principles Header Callout */}
        <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-4 border border-indigo-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg shadow-indigo-950/20">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-bold text-white tracking-wide">
                Human-in-the-Loop Decision Principle
              </div>
              <p className="text-xs text-slate-400">
                AI flags the risk signal. Evidence explains the variance. Reviewing officers make the administrative decision.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              Isolation Forest + NLP miniLM
            </span>
            <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              eSAKSHI Rule Engine
            </span>
          </div>
        </div>

        {/* ─── Top Level KPI Metrics Bar ─── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 shadow-sm hover:border-slate-700 transition">
            <div className="text-[11px] font-medium text-slate-400">Total Sanctioned</div>
            <div className="text-lg font-black text-white mt-1">
              {formatINR(dashboardSummary?.total_sanctioned_amount || 83339905622)}
            </div>
            <div className="text-[10px] text-cyan-400 mt-1 flex items-center gap-1 font-medium">
              543 MPs Nationwide
            </div>
          </div>

          <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 shadow-sm hover:border-slate-700 transition">
            <div className="text-[11px] font-medium text-slate-400">Monitored Works</div>
            <div className="text-lg font-black text-white mt-1">
              {dashboardSummary?.total_projects || 200}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              Expenditure: {formatINR(dashboardSummary?.total_expenditure || 268000000)}
            </div>
          </div>

          <div className="bg-slate-900/90 rounded-xl p-4 border border-rose-900/40 shadow-sm hover:border-rose-800/60 transition bg-gradient-to-b from-rose-950/20 to-transparent">
            <div className="text-[11px] font-medium text-rose-300 flex items-center justify-between">
              Critical Signals
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
            </div>
            <div className="text-lg font-black text-rose-400 mt-1">
              {dashboardSummary?.critical_risk_count || 4}
            </div>
            <div className="text-[10px] text-rose-300/80 mt-1 font-medium">
              Immediate Review Req.
            </div>
          </div>

          <div className="bg-slate-900/90 rounded-xl p-4 border border-amber-900/40 shadow-sm hover:border-amber-800/60 transition bg-gradient-to-b from-amber-950/20 to-transparent">
            <div className="text-[11px] font-medium text-amber-300">High Risk Signals</div>
            <div className="text-lg font-black text-amber-400 mt-1">
              {dashboardSummary?.high_risk_count || 11}
            </div>
            <div className="text-[10px] text-amber-300/80 mt-1 font-medium">
              Field Verification Priority
            </div>
          </div>

          <div className="bg-slate-900/90 rounded-xl p-4 border border-indigo-900/40 shadow-sm hover:border-indigo-800/60 transition">
            <div className="text-[11px] font-medium text-indigo-300">Verification Cases</div>
            <div className="text-lg font-black text-indigo-400 mt-1">
              {cases.length || 156}
            </div>
            <div className="text-[10px] text-indigo-300/80 mt-1 font-medium">
              Active in Officer Queue
            </div>
          </div>

          <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 shadow-sm hover:border-slate-700 transition">
            <div className="text-[11px] font-medium text-slate-400">Data Quality Alerts</div>
            <div className="text-lg font-black text-yellow-400 mt-1">
              {dashboardSummary?.data_quality_issues || 2}
            </div>
            <div className="text-[10px] text-yellow-500/80 mt-1 font-medium">
              Missing amounts & dupes
            </div>
          </div>
        </div>

        {/* ─── TAB 1: EXECUTIVE OVERVIEW ─── */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Risk Distribution Breakdown */}
              <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg">
                <h2 className="text-sm font-bold text-white mb-4 flex items-center justify-between">
                  Risk Tier Distribution
                  <span className="text-[11px] font-normal text-slate-400">MPLADS & Projects</span>
                </h2>

                <div className="space-y-3.5">
                  {[
                    { label: "Critical Risk (80–100)", count: 4, pct: "0.5%", color: "bg-rose-500", text: "text-rose-400" },
                    { label: "High Risk (60–79)", count: 11, pct: "1.5%", color: "bg-amber-500", text: "text-amber-400" },
                    { label: "Moderate Risk (30–59)", count: 165, pct: "22.2%", color: "bg-yellow-500", text: "text-yellow-400" },
                    { label: "Low / Normal (0–29)", count: 563, pct: "75.8%", color: "bg-emerald-500", text: "text-emerald-400" },
                  ].map((item, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-slate-300">{item.label}</span>
                        <span className={`font-bold ${item.text}`}>
                          {item.count} ({item.pct})
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className={`h-full ${item.color} rounded-full`}
                          style={{ width: item.pct }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400">
                  <div className="font-semibold text-slate-300 mb-1">Analytical Dimensions:</div>
                  <ul className="list-disc pl-4 space-y-0.5 text-[10px]">
                    <li>Financial Anomaly: Isolation Forest on peer expenditure variance</li>
                    <li>Timeline Discrepancy: Expected completion vs elapsed days</li>
                    <li>Disbursement Consistency: Payment–Progress gap analysis</li>
                    <li>Duplicate Proposals: Semantic work similarity comparison</li>
                  </ul>
                </div>
              </div>

              {/* State-wise Allocation & Risk Intensity */}
              <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg lg:col-span-2">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    State-Level Risk & Allocation Intensity
                  </h2>
                  <span className="text-xs text-slate-400">Top States by Monitored Allocation</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-2 font-semibold">State / UT</th>
                        <th className="pb-2 font-semibold">MPs</th>
                        <th className="pb-2 font-semibold">Total Allocation</th>
                        <th className="pb-2 font-semibold">High Risk MPs</th>
                        <th className="pb-2 font-semibold">Outliers</th>
                        <th className="pb-2 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {(stateSummary.length > 0
                        ? stateSummary
                        : [
                            { state: "Uttar Pradesh", total_mps: 80, total_allocation: 12000000000, high_risk_mps: 2, outlier_mps: 1 },
                            { state: "Maharashtra", total_mps: 48, total_allocation: 7200000000, high_risk_mps: 3, outlier_mps: 2 },
                            { state: "West Bengal", total_mps: 42, total_allocation: 6300000000, high_risk_mps: 1, outlier_mps: 1 },
                            { state: "Bihar", total_mps: 40, total_allocation: 6000000000, high_risk_mps: 2, outlier_mps: 1 },
                            { state: "Tamil Nadu", total_mps: 39, total_allocation: 5850000000, high_risk_mps: 1, outlier_mps: 0 },
                          ]
                      ).map((st, i) => (
                        <tr key={i} className="hover:bg-slate-800/40 transition">
                          <td className="py-2.5 font-bold text-white">{st.state}</td>
                          <td className="py-2.5 text-slate-300">{st.total_mps}</td>
                          <td className="py-2.5 font-mono text-slate-200">{formatINR(st.total_allocation)}</td>
                          <td className="py-2.5">
                            {st.high_risk_mps > 0 ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                {st.high_risk_mps} Flagged
                              </span>
                            ) : (
                              <span className="text-slate-500 text-[10px]">0</span>
                            )}
                          </td>
                          <td className="py-2.5 text-slate-400">{st.outlier_mps || 0}</td>
                          <td className="py-2.5">
                            <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                              Active
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Quick Priority Alert Stream */}
            <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></div>
                  <h2 className="text-sm font-bold text-white">High Priority Risk Signals Requiring Action</h2>
                </div>
                <button
                  onClick={() => setActiveTab("alerts")}
                  className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
                >
                  View all alerts &rarr;
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {alerts.slice(0, 3).map((alt, i) => (
                  <div
                    key={i}
                    className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition space-y-2.5 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono font-bold text-slate-400">
                          {alt.project_id}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-950 text-rose-400 border border-rose-800">
                          SCORE {alt.risk_score}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-white mt-1.5">
                        {alt.primary_signal}
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                        {alt.work_description}
                      </p>
                    </div>

                    <div className="border-t border-slate-800/80 pt-2 flex items-center justify-between text-[10px] text-slate-400">
                      <span>{alt.district}, {alt.state}</span>
                      <span className="font-semibold text-slate-200">{formatINR(alt.sanctioned_amount)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── TAB 2: RISK ALERTS INBOX ─── */}
        {activeTab === "alerts" && (
          <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-base font-bold text-white">Risk Alerts Inbox</h2>
                <p className="text-xs text-slate-400">
                  Prioritized stream of statistical, operational, and financial risk signals.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                {["ALL", "CRITICAL", "HIGH", "MODERATE"].map((lvl) => (
                  <button
                    key={lvl}
                    onClick={() => setAlertFilter(lvl)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                      alertFilter === lvl
                        ? "bg-cyan-500 text-slate-950 shadow-md"
                        : "bg-slate-800 text-slate-400 hover:text-white"
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              {alerts
                .filter((a) => alertFilter === "ALL" || a.risk_level === alertFilter)
                .map((alt, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/90 hover:border-slate-700 transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            alt.risk_level === "CRITICAL"
                              ? "bg-rose-950 text-rose-400 border border-rose-800"
                              : alt.risk_level === "HIGH"
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-yellow-950 text-yellow-400 border border-yellow-800"
                          }`}
                        >
                          {alt.risk_level}
                        </span>
                        <span className="font-mono text-xs text-slate-400">{alt.project_id}</span>
                        <span className="text-xs text-slate-500">•</span>
                        <span className="text-xs text-slate-300 font-medium">
                          {alt.district}, {alt.state}
                        </span>
                        <span className="text-xs text-slate-500">•</span>
                        <span className="text-xs text-cyan-400 font-medium">MP: {alt.mp_name}</span>
                      </div>

                      <div className="text-sm font-semibold text-white">
                        {alt.primary_signal}
                      </div>

                      <p className="text-xs text-slate-400">
                        {alt.work_description}
                      </p>

                      <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 pt-1">
                        <span>
                          Sanctioned: <b className="text-slate-200">{formatINR(alt.sanctioned_amount)}</b>
                        </span>
                        <span>•</span>
                        <span>
                          Physical Progress: <b className="text-slate-200">{alt.physical_progress_pct?.toFixed(1)}%</b>
                        </span>
                        <span>•</span>
                        <span>
                          Financial Util.: <b className="text-slate-200">{(alt.utilization_ratio * 100)?.toFixed(1)}%</b>
                        </span>
                        <span>•</span>
                        <span>
                          Delay: <b className="text-rose-400">{alt.delay_days || 0} days</b>
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                      <button
                        onClick={() => {
                          setActiveTab("inspector");
                          setInspectQuery(alt.project_id);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
                      >
                        Inspect Evidence
                      </button>
                      <button
                        onClick={() => {
                          handleVerificationDecision(alt.alert_id, "ACTION_REQUIRED");
                        }}
                        className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-xs font-semibold text-rose-300 border border-rose-500/40 transition"
                      >
                        Flag for Field Audit
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* ─── TAB 3: PROJECT WORKS DIRECTORY ─── */}
        {activeTab === "projects" && (
          <div className="space-y-6">
            <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg space-y-4">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold text-white">MPLADS Project Works</h2>
                  <p className="text-xs text-slate-400">
                    Comprehensive inventory of works with progress, financial utilization, and risk indicators.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5 w-full sm:w-auto">
                  <input
                    type="text"
                    placeholder="Search work, MP, district..."
                    value={projectSearch}
                    onChange={(e) => setProjectSearch(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-full sm:w-60"
                  />
                  <select
                    value={projectRiskFilter}
                    onChange={(e) => setProjectRiskFilter(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="ALL">All Risk Levels</option>
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MODERATE">Moderate</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2.5 font-semibold">Work ID</th>
                      <th className="pb-2.5 font-semibold">Description</th>
                      <th className="pb-2.5 font-semibold">Location / MP</th>
                      <th className="pb-2.5 font-semibold">Sanctioned</th>
                      <th className="pb-2.5 font-semibold">Physical vs Financial</th>
                      <th className="pb-2.5 font-semibold">Delay</th>
                      <th className="pb-2.5 font-semibold">Risk Level</th>
                      <th className="pb-2.5 font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {projects
                      .filter((p) => {
                        const matchesSearch =
                          !projectSearch ||
                          p.work_description.toLowerCase().includes(projectSearch.toLowerCase()) ||
                          p.mp_name.toLowerCase().includes(projectSearch.toLowerCase()) ||
                          p.district.toLowerCase().includes(projectSearch.toLowerCase()) ||
                          p.project_id.toLowerCase().includes(projectSearch.toLowerCase());
                        const matchesRisk =
                          projectRiskFilter === "ALL" || p.risk_level === projectRiskFilter;
                        return matchesSearch && matchesRisk;
                      })
                      .map((proj, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 font-mono font-bold text-slate-300">
                            {proj.project_id}
                          </td>
                          <td className="py-3 max-w-xs truncate text-white font-medium">
                            {proj.work_description}
                          </td>
                          <td className="py-3 text-slate-300">
                            <div>{proj.district}, {proj.state}</div>
                            <div className="text-[10px] text-cyan-400">{proj.mp_name}</div>
                          </td>
                          <td className="py-3 font-mono text-slate-200">
                            {formatINR(proj.sanctioned_amount)}
                          </td>
                          <td className="py-3 min-w-[140px]">
                            <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                              <span>P: {proj.physical_progress_pct?.toFixed(0)}%</span>
                              <span>F: {((proj.utilization_ratio || 0) * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden flex">
                              <div
                                className="bg-cyan-500 h-full"
                                style={{ width: `${Math.min(100, proj.physical_progress_pct || 0)}%` }}
                              ></div>
                            </div>
                          </td>
                          <td className="py-3 font-mono">
                            {proj.delay_days > 0 ? (
                              <span className="text-rose-400 font-semibold">{proj.delay_days}d</span>
                            ) : (
                              <span className="text-emerald-400 font-semibold">On Time</span>
                            )}
                          </td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                proj.risk_level === "CRITICAL"
                                  ? "bg-rose-950 text-rose-400 border border-rose-800"
                                  : proj.risk_level === "HIGH"
                                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                                  : proj.risk_level === "MODERATE"
                                  ? "bg-yellow-950 text-yellow-400 border border-yellow-800"
                                  : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              }`}
                            >
                              {proj.risk_level} ({proj.risk_score})
                            </span>
                          </td>
                          <td className="py-3">
                            <button
                              onClick={() => handleSelectProject(proj)}
                              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-semibold text-cyan-400 border border-slate-700 transition"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Selected Project Inspection Drawer */}
            {selectedProject && (
              <div className="bg-slate-900/90 rounded-2xl p-6 border border-cyan-500/40 shadow-2xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <span className="text-xs font-mono text-cyan-400 font-bold">{selectedProject.project_id}</span>
                    <h3 className="text-base font-bold text-white mt-0.5">{selectedProject.work_description}</h3>
                  </div>
                  <button
                    onClick={() => setSelectedProject(null)}
                    className="text-slate-400 hover:text-white p-1"
                  >
                    ✕
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Financial Sanction</div>
                    <div className="text-base font-bold text-white mt-1">{formatINR(selectedProject.sanctioned_amount)}</div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Expended: {formatINR(selectedProject.expenditure_amount)}
                    </div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Progress Comparison</div>
                    <div className="text-base font-bold text-cyan-400 mt-1">
                      {selectedProject.physical_progress_pct?.toFixed(1)}% Physical
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Utilization: {((selectedProject.utilization_ratio || 0) * 100).toFixed(1)}%
                    </div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Timeline Metrics</div>
                    <div className="text-base font-bold text-rose-400 mt-1">
                      {selectedProject.delay_days || 0} Days Delay
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      Project Age: {selectedProject.project_age_days} days
                    </div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-slate-400 text-[11px]">Overall AI Risk Score</div>
                    <div className="text-base font-bold text-amber-400 mt-1">
                      {selectedProject.risk_score} / 100
                    </div>
                    <div className="text-[10px] text-amber-300 mt-1 font-semibold">
                      {selectedProject.risk_level} TIER
                    </div>
                  </div>
                </div>

                {/* Similar works detection */}
                {similarWorks.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-800">
                    <h4 className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                      <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                      </svg>
                      Potentially Similar / Overlapping Works in Peer Vicinity
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {similarWorks.slice(0, 2).map((sim, i) => (
                        <div key={i} className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-xs">
                          <div className="flex justify-between items-center text-slate-400 text-[10px]">
                            <span>{sim.project_id}</span>
                            <span className="text-cyan-400 font-bold">{(sim.similarity_score * 100).toFixed(0)}% Similarity</span>
                          </div>
                          <p className="text-slate-200 mt-1 font-medium">{sim.work_description}</p>
                          <div className="text-[10px] text-slate-500 mt-1">
                            Amount: {formatINR(sim.sanctioned_amount)} | {sim.district}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 4: MP ALLOCATIONS INTELLIGENCE ─── */}
        {activeTab === "mps" && (
          <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  Official Hon&apos;ble MP Allocations Audit
                  <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30">
                    543 Members of Parliament
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  Data ingested directly from official MPLADS allocation schedule. Isolation Forest anomaly scores evaluated against state & national peer groups.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Search MP or Constituency..."
                  value={mpSearch}
                  onChange={(e) => setMpSearch(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
                <button
                  onClick={() => setMpOutlierOnly(!mpOutlierOnly)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    mpOutlierOnly
                      ? "bg-rose-500/20 text-rose-300 border-rose-500/50"
                      : "bg-slate-800 text-slate-400 border-slate-700 hover:text-white"
                  }`}
                >
                  {mpOutlierOnly ? "Showing Outliers Only" : "Filter Outliers"}
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-2.5 font-semibold">Sr.</th>
                    <th className="pb-2.5 font-semibold">Hon&apos;ble MP Name</th>
                    <th className="pb-2.5 font-semibold">Constituency</th>
                    <th className="pb-2.5 font-semibold">State / UT</th>
                    <th className="pb-2.5 font-semibold">Allocated Limit (₹)</th>
                    <th className="pb-2.5 font-semibold">Anomaly Score</th>
                    <th className="pb-2.5 font-semibold">Peer Dev.</th>
                    <th className="pb-2.5 font-semibold">Data Quality</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {mpAllocations
                    .filter((m) => {
                      const matchesSearch =
                        !mpSearch ||
                        m.mp_name.toLowerCase().includes(mpSearch.toLowerCase()) ||
                        m.constituency_clean.toLowerCase().includes(mpSearch.toLowerCase()) ||
                        m.state.toLowerCase().includes(mpSearch.toLowerCase());
                      const matchesOutlier = !mpOutlierOnly || m.is_financial_outlier;
                      return matchesSearch && matchesOutlier;
                    })
                    .map((mp, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40 transition">
                        <td className="py-2.5 text-slate-500 font-mono">{mp.sr_no}</td>
                        <td className="py-2.5 font-bold text-white">{mp.mp_name}</td>
                        <td className="py-2.5 text-slate-300">{mp.constituency_clean}</td>
                        <td className="py-2.5 text-slate-400">{mp.state}</td>
                        <td className="py-2.5 font-mono text-slate-200">
                          {mp.allocated_amount_inr > 0 ? (
                            formatINR(mp.allocated_amount_inr)
                          ) : (
                            <span className="text-rose-400 font-bold">MISSING IN RAW DATA</span>
                          )}
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              mp.anomaly_score > 70
                                ? "bg-rose-950 text-rose-300 border border-rose-800"
                                : mp.anomaly_score > 40
                                ? "bg-amber-950 text-amber-300 border border-amber-800"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {mp.anomaly_score?.toFixed(1) || "0.0"}
                          </span>
                        </td>
                        <td className="py-2.5 font-mono text-slate-400">
                          {mp.state_peer_deviation_pct
                            ? `${mp.state_peer_deviation_pct > 0 ? "+" : ""}${mp.state_peer_deviation_pct.toFixed(1)}%`
                            : "0.0%"}
                        </td>
                        <td className="py-2.5">
                          {mp.is_missing_amount || mp.is_duplicate_constituency ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-950 text-yellow-300 border border-yellow-800">
                              {mp.is_missing_amount ? "MISSING VALUE" : "DUPLICATE ENTRY"}
                            </span>
                          ) : (
                            <span className="text-emerald-400 text-[10px] font-medium">✓ Clean</span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ─── TAB 5: HUMAN VERIFICATION DESK ─── */}
        {activeTab === "verification" && (
          <div className="bg-slate-900/80 rounded-2xl p-5 border border-slate-800 shadow-lg space-y-4">
            <div className="border-b border-slate-800 pb-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Human-in-the-Loop Officer Decision Desk
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                  {cases.length} Open Cases
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Official audit review queue. Government officers evaluate generated risk evidence and render administrative verification verdicts.
              </p>
            </div>

            <div className="space-y-3.5">
              {cases.map((c, i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-slate-950 border border-slate-800/90 hover:border-slate-700 transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-cyan-400">{c.case_id}</span>
                      <span className="text-xs text-slate-500">•</span>
                      <span className="text-xs font-mono text-slate-300">{c.entity_id}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.priority === "URGENT"
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : "bg-amber-950 text-amber-300 border border-amber-800"
                        }`}
                      >
                        {c.priority} PRIORITY
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                        STATUS: {c.status}
                      </span>
                    </div>

                    <div className="text-sm font-semibold text-white">
                      Primary Flag: {c.primary_signal}
                    </div>

                    <div className="text-xs text-slate-400">
                      Risk Tier: <span className="text-amber-400 font-bold">{c.risk_level}</span> (Score: {c.risk_score})
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => handleVerificationDecision(c.case_id, "VERIFIED")}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-xs font-bold text-emerald-300 border border-emerald-500/40 transition"
                    >
                      ✓ Mark Verified
                    </button>
                    <button
                      onClick={() => handleVerificationDecision(c.case_id, "ACTION_REQUIRED")}
                      className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-xs font-bold text-rose-300 border border-rose-500/40 transition"
                    >
                      ⚠ Action Required
                    </button>
                    <button
                      onClick={() => handleVerificationDecision(c.case_id, "FALSE_SIGNAL")}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 border border-slate-700 transition"
                    >
                      False Signal
                    </button>
                    <button
                      onClick={() => handleVerificationDecision(c.case_id, "RESOLVED")}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-xs font-bold text-indigo-300 border border-indigo-500/40 transition"
                    >
                      Resolve
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ─── TAB 6: EXPLAINABLE AI INSPECTOR ─── */}
        {activeTab === "inspector" && (
          <div className="bg-slate-900/80 rounded-2xl p-6 border border-slate-800 shadow-lg space-y-6">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Explainable AI Evidence Generator & Inspector
              </h2>
              <p className="text-xs text-slate-400">
                Transparent &quot;Why was it flagged?&quot; audit trail for any project work or MP allocation record.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="Enter Project ID (e.g. MPLADS-MA-2025-0001)..."
                value={inspectQuery}
                onChange={(e) => setInspectQuery(e.target.value)}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <button
                onClick={handleInspectQuery}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-sm font-bold text-white shadow-lg shadow-cyan-600/20 transition active:scale-95"
              >
                Inspect Risk Trail
              </button>
            </div>

            {inspectResult && (
              <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
                {inspectResult.error ? (
                  <div className="text-rose-400 text-xs font-semibold">{inspectResult.error}</div>
                ) : (
                  <>
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div>
                        <span className="font-mono text-xs text-cyan-400 font-bold">{inspectResult.project?.project_id}</span>
                        <h4 className="text-sm font-bold text-white mt-0.5">{inspectResult.project?.work_description}</h4>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-bold ${
                          inspectResult.risk_score?.risk_level === "CRITICAL"
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : inspectResult.risk_score?.risk_level === "HIGH"
                            ? "bg-amber-950 text-amber-300 border border-amber-800"
                            : "bg-yellow-950 text-yellow-300 border border-yellow-800"
                        }`}
                      >
                        {inspectResult.risk_score?.risk_level} (Score: {inspectResult.risk_score?.overall_score})
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Financial Risk</div>
                        <div className="font-bold text-white mt-1">{inspectResult.risk_score?.financial_risk?.toFixed(1) || 0}</div>
                      </div>
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Progress Gap Risk</div>
                        <div className="font-bold text-white mt-1">{inspectResult.risk_score?.progress_risk?.toFixed(1) || 0}</div>
                      </div>
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Timeline Risk</div>
                        <div className="font-bold text-white mt-1">{inspectResult.risk_score?.timeline_risk?.toFixed(1) || 0}</div>
                      </div>
                      <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <div className="text-slate-400 text-[10px]">Rules Compliance</div>
                        <div className="font-bold text-white mt-1">{inspectResult.risk_score?.rule_risk?.toFixed(1) || 0}</div>
                      </div>
                    </div>

                    {inspectResult.explanation && (
                      <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/20 text-xs">
                        <div className="font-bold text-indigo-300 mb-1">Explainable AI Evidence Summary:</div>
                        <p className="text-slate-300 leading-relaxed">{inspectResult.explanation}</p>
                      </div>
                    )}

                    {inspectResult.recommended_verification && inspectResult.recommended_verification.length > 0 && (
                      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1">
                        <div className="font-bold text-cyan-400">Recommended Field Audit Actions:</div>
                        <ul className="list-disc pl-4 space-y-0.5 text-slate-300 text-[11px]">
                          {inspectResult.recommended_verification.map((rec: string, i: number) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
