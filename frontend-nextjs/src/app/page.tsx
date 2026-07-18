'use client';
import { useState, useMemo, useEffect } from 'react';
import { 
  LayoutDashboard, Play, Database, FileText, 
  Download, CheckCircle2, AlertCircle, RefreshCw,
  Search, ChevronRight, Activity, FileSpreadsheet, Box
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend
} from 'recharts';

interface Deal {
  target_company?: string;
  buyer?: string;
  deal_type?: string;
  value?: string;
  country?: string;
  industry?: string;
  summary?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data state
  const [deals, setDeals] = useState<Deal[]>([]);
  const [newsletter, setNewsletter] = useState('');
  const [stats, setStats] = useState<any>(null);
  
  // UI state
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState<'success' | 'error' | 'info'>('info');
  const [searchQuery, setSearchQuery] = useState('');
  const [targetDate, setTargetDate] = useState('');

  // Initial load
  useEffect(() => {
    fetchStats();
    handleLoadPrevious(true); // silent load on mount
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/db/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  const [currentStep, setCurrentStep] = useState(0);

  // Pipeline Logic
  const handleRunPipeline = async () => {
    setIsRunning(true);
    setCurrentStep(1);
    setStatusMessage('Engaging AI Agents... (This takes 1-2 minutes)');
    setStatusType('info');
    
    // Simulate real-time progress since the backend endpoint is a single blocking call
    const timers = [
      setTimeout(() => setCurrentStep(2), 3000),   // Fetching finishes fast
      setTimeout(() => setCurrentStep(3), 8000),   // Deduplication
      setTimeout(() => setCurrentStep(4), 18000),  // Relevance Filtering
      // Extraction takes the longest, so it stays on step 4 until fetch resolves
    ];

    try {
      const response = await fetch(`${API_BASE_URL}/run-pipeline`, { method: 'POST' });
      if (!response.ok) throw new Error('Pipeline execution failed');
      
      timers.forEach(clearTimeout);
      setCurrentStep(5); // Jump to generating newsletter / complete
      
      const data = await response.json();
      setDeals(data.deals || []);
      setNewsletter(data.newsletter || '');
      setStatusMessage(`Pipeline completed! Extracted ${data.deals?.length || 0} deals.`);
      setStatusType('success');
      fetchStats();
      
      // Navigate to database after a brief delay so user sees 100% completion
      setTimeout(() => {
        setActiveTab('database');
        setCurrentStep(0);
      }, 1500);

    } catch (error) {
      timers.forEach(clearTimeout);
      console.error(error);
      setStatusMessage('Error executing AI pipeline');
      setStatusType('error');
      setCurrentStep(0);
    } finally {
      setIsRunning(false);
    }
  };

  const handleLoadPrevious = async (silent = false) => {
    if (!silent) {
      setIsRunning(true);
      setStatusMessage('Loading database...');
      setStatusType('info');
    }
    try {
      const dealsRes = await fetch(`${API_BASE_URL}/deals?source=mongo`);
      if (dealsRes.ok) {
        const dealsData = await dealsRes.json();
        setDeals(dealsData.deals || []);
      }
      const newsRes = await fetch(`${API_BASE_URL}/newsletter?source=mongo`);
      if (newsRes.ok) {
        const newsData = await newsRes.json();
        setNewsletter(newsData.newsletter || '');
      }
      if (!silent) {
        setStatusMessage('Loaded historical data successfully.');
        setStatusType('success');
      }
    } catch (error) {
      if (!silent) {
        setStatusMessage('Failed to connect to MongoDB.');
        setStatusType('error');
      }
    } finally {
      if (!silent) setIsRunning(false);
    }
  };

  const handleDownload = async (format: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/exports/${format}`);
      if (!response.ok) throw new Error('Export not found');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FMCG-Intelligence.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed", error);
      alert("Failed to download file. Please run the pipeline first.");
    }
  };

  // Chart Data Processing
  const formatChartLabel = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('acquisition') && l.includes('minority')) return 'Minority Stake';
    if (l.includes('acquisition') && l.includes('majority')) return 'Majority Stake';
    if (l.includes('joint venture') || l.includes('jv')) return 'Joint Venture';
    if (l.includes('strategic investment')) return 'Strategic Investment';
    if (l.includes('funding') || l.includes('fund')) return 'Funding Round';
    if (l.includes('acquisition') || l.includes('buy')) return 'Acquisition';
    if (l.includes('partnership')) return 'Partnership';
    if (l.includes('merger')) return 'Merger';
    if (l.length > 25) return l.substring(0, 22) + '...';
    return label.charAt(0).toUpperCase() + label.slice(1);
  };

  const chartData = useMemo(() => {
    if (!deals.length) return [];
    const typeCount: Record<string, number> = {};
    deals.forEach(d => {
      const t = formatChartLabel(d.deal_type || 'Unknown');
      typeCount[t] = (typeCount[t] || 0) + 1;
    });
    return Object.entries(typeCount)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [deals]);

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  // Render Helpers
  const renderSidebarItem = (id: string, icon: any, label: string) => {
    const Icon = icon;
    const isActive = activeTab === id;
    return (
      <button
        onClick={() => setActiveTab(id)}
        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium ${
          isActive 
            ? 'bg-blue-50 text-blue-700' 
            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
        }`}
      >
        <Icon className="w-5 h-5" />
        {label}
      </button>
    );
  };

  const filteredDeals = deals.filter(d => 
    (d.target_company?.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (d.buyer?.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6">
          <div className="flex items-center gap-3 text-slate-900">
            <div className="bg-blue-600 p-2 rounded-lg text-white">
              <Activity className="w-6 h-6" />
            </div>
            <h1 className="font-bold text-xl tracking-tight leading-tight">FMCG<br/>Intelligence</h1>
          </div>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {renderSidebarItem('overview', LayoutDashboard, 'Overview')}
          {renderSidebarItem('pipeline', Play, 'Run Pipeline')}
          {renderSidebarItem('database', Database, 'Extracted Deals')}
          {renderSidebarItem('reports', FileText, 'Newsletter & Exports')}
        </nav>
        
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        
        {/* Header bar */}
        <header className="bg-white border-b border-slate-200 px-8 py-5 flex items-center justify-between sticky top-0 z-10">
          <h2 className="text-2xl font-bold text-slate-800 capitalize">
            {activeTab.replace('-', ' ')}
          </h2>
          <div className="flex items-center gap-4">
            {statusMessage && (
              <div className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 ${
                statusType === 'success' ? 'bg-emerald-50 text-emerald-700' :
                statusType === 'error' ? 'bg-red-50 text-red-700' :
                'bg-blue-50 text-blue-700'
              }`}>
                {statusType === 'info' && <RefreshCw className="w-4 h-4 animate-spin" />}
                {statusType === 'success' && <CheckCircle2 className="w-4 h-4" />}
                {statusType === 'error' && <AlertCircle className="w-4 h-4" />}
                {statusMessage}
              </div>
            )}
            <button 
              onClick={() => handleLoadPrevious(false)}
              className="px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-50 transition flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Sync DB
            </button>
          </div>
        </header>

        {/* Tab Content */}
        <div className="p-8 w-full">

          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              {/* Metric Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                
                <div className="bg-gradient-to-br from-white to-slate-50 p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                    <Database className="w-24 h-24 text-slate-800" />
                  </div>
                  <p className="text-sm font-semibold text-slate-500 relative z-10">Raw Articles Ingested</p>
                  <p className="text-4xl font-bold text-slate-900 mt-2 relative z-10">{stats?.raw_articles || 0}</p>
                </div>

                <div className="bg-gradient-to-br from-white to-blue-50/30 p-6 rounded-2xl border border-blue-100 shadow-sm hover:shadow-md hover:shadow-blue-100 hover:-translate-y-1 transition-all duration-300 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                    <Activity className="w-24 h-24 text-blue-600" />
                  </div>
                  <p className="text-sm font-semibold text-blue-600/80 relative z-10">Deals Extracted</p>
                  <p className="text-4xl font-bold text-blue-600 mt-2 relative z-10">{stats?.deals || deals.length}</p>
                </div>

                <div className="bg-gradient-to-br from-white to-emerald-50/30 p-6 rounded-2xl border border-emerald-100 shadow-sm hover:shadow-md hover:shadow-emerald-100 hover:-translate-y-1 transition-all duration-300 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                    <FileText className="w-24 h-24 text-emerald-600" />
                  </div>
                  <p className="text-sm font-semibold text-emerald-600/80 relative z-10">Newsletters Built</p>
                  <p className="text-4xl font-bold text-emerald-600 mt-2 relative z-10">{stats?.newsletters || 0}</p>
                </div>

                <div className="bg-gradient-to-br from-white to-purple-50/30 p-6 rounded-2xl border border-purple-100 shadow-sm hover:shadow-md hover:shadow-purple-100 hover:-translate-y-1 transition-all duration-300 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-10 transition-opacity">
                    <Play className="w-24 h-24 text-purple-600" />
                  </div>
                  <p className="text-sm font-semibold text-purple-600/80 relative z-10">Pipeline Runs</p>
                  <p className="text-4xl font-bold text-purple-600 mt-2 relative z-10">{stats?.pipeline_runs || 0}</p>
                </div>

              </div>

              {/* Chart Section */}
              <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm flex flex-col items-center">
                <h3 className="text-xl font-bold text-slate-900 mb-2 text-left w-full">Deal Distribution by Type</h3>
                <p className="text-slate-500 text-sm mb-6 w-full text-left">Overview of extracted FMCG transactions</p>
                
                <div className="h-[350px] w-full max-w-3xl">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={chartData}
                          cx="50%"
                          cy="45%"
                          innerRadius={90}
                          outerRadius={130}
                          paddingAngle={5}
                          dataKey="value"
                          stroke="none"
                        >
                          {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          formatter={(value, name) => [`${value} Deals`, name]}
                          contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)' }}
                        />
                        <Legend 
                          verticalAlign="bottom" 
                          height={36} 
                          iconType="circle"
                          wrapperStyle={{ paddingTop: '20px' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400">
                      <Box className="w-12 h-12 mb-3 text-slate-300" />
                      <p>No chart data available.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* PIPELINE TAB */}
          {activeTab === 'pipeline' && (
            <div className="bg-white p-10 rounded-3xl border border-slate-200 shadow-sm max-w-3xl mx-auto animate-in fade-in zoom-in-95 duration-300">
              <div className="text-center border-b border-slate-100 pb-8 mb-8">
                <div className="w-20 h-20 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Play className="w-10 h-10 ml-2" />
                </div>
                <h2 className="text-3xl font-bold text-slate-900 mb-4">Run Autonomous Pipeline</h2>
                <p className="text-slate-500 text-lg mb-8 max-w-lg mx-auto">
                  Trigger the AI agents to scrape the web, deduplicate articles, evaluate credibility, and extract FMCG deal structures.
                </p>
                
                <button
                  onClick={handleRunPipeline}
                  disabled={isRunning}
                  className="w-full sm:w-auto px-10 py-5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg rounded-2xl transition-all disabled:opacity-50 shadow-lg shadow-blue-200 hover:shadow-blue-300 flex items-center justify-center gap-3 mx-auto"
                >
                  {isRunning ? (
                    <><RefreshCw className="w-6 h-6 animate-spin" /> Processing AI Pipeline...</>
                  ) : (
                    <>Start AI Agents <ChevronRight className="w-6 h-6" /></>
                  )}
                </button>
              </div>

              {/* Fancy Animated Step Tracker */}
              <div className="max-w-md mx-auto space-y-6">
                {[
                  { id: 1, label: 'Fetching Public RSS Feeds' },
                  { id: 2, label: 'Cleaning & Deduplication' },
                  { id: 3, label: 'Semantic Relevance Filtering' },
                  { id: 4, label: 'Extracting Deals via Sonar LLM' },
                  { id: 5, label: 'Drafting Executive Newsletter & Saving' }
                ].map((step) => {
                  const isActive = currentStep === step.id;
                  const isCompleted = currentStep > step.id;
                  const isPending = currentStep > 0 && currentStep < step.id;
                  const isIdle = currentStep === 0;

                  return (
                    <div 
                      key={step.id} 
                      className={`flex items-center gap-5 transition-all duration-500 ${
                        isActive ? 'scale-105 transform' : ''
                      }`}
                    >
                      {/* Step Indicator Bubble */}
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors duration-500 shadow-sm ${
                        isCompleted ? 'bg-emerald-100 text-emerald-600' :
                        isActive ? 'bg-blue-600 text-white shadow-blue-200 shadow-lg ring-4 ring-blue-50' :
                        isPending ? 'bg-slate-100 text-slate-400' :
                        'bg-slate-50 text-slate-300'
                      }`}>
                        {isCompleted ? <CheckCircle2 className="w-6 h-6" /> : <span className="font-bold text-lg">{step.id}</span>}
                      </div>

                      {/* Step Text & Spinner */}
                      <div className={`flex items-center justify-between w-full font-medium text-lg transition-colors duration-500 ${
                        isCompleted ? 'text-emerald-700' :
                        isActive ? 'text-blue-700 font-bold' :
                        isPending ? 'text-slate-500' :
                        'text-slate-300'
                      }`}>
                        {step.label}
                        {isActive && <RefreshCw className="w-5 h-5 animate-spin text-blue-500 shrink-0" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* DATABASE TAB */}
          {activeTab === 'database' && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[calc(100vh-180px)]">
              <div className="p-4 border-b border-slate-200 flex items-center gap-4">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input 
                    type="text" 
                    placeholder="Search by company or buyer..." 
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <div className="text-sm font-medium text-slate-500">
                  {filteredDeals.length} Deals Found
                </div>
              </div>
              
              <div className="flex-1 overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 sticky top-0 text-slate-600 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4">Target Company</th>
                      <th className="px-6 py-4">Buyer / Investor</th>
                      <th className="px-6 py-4">Deal Type</th>
                      <th className="px-6 py-4">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredDeals.map((deal, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4 font-bold text-slate-900">{deal.target_company || '-'}</td>
                        <td className="px-6 py-4 text-slate-700">{deal.buyer || '-'}</td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-bold">
                            {deal.deal_type || '-'}
                          </span>
                        </td>
                        <td className="px-6 py-4 font-medium text-emerald-600">{deal.value || '-'}</td>
                      </tr>
                    ))}
                    {filteredDeals.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-20 text-center text-slate-400">
                          <Box className="w-12 h-12 mx-auto mb-3 opacity-20" />
                          No deals matched your search.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* REPORTS TAB */}
          {activeTab === 'reports' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              
              {/* Newsletter Reader */}
              <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[calc(100vh-180px)]">
                <div className="px-8 py-5 border-b border-slate-200 bg-slate-50 flex items-center gap-3">
                  <FileText className="w-5 h-5 text-slate-500" />
                  <h3 className="font-bold text-slate-800">Intelligence Briefing</h3>
                </div>
                <div className="flex-1 overflow-auto p-8 font-sans leading-relaxed text-slate-800 text-lg">
                  {newsletter ? newsletter.split('\n').map((line, i) => {
                    const parsedLine = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                    if (line.startsWith('## ')) return <h2 key={i} className="text-2xl font-bold text-slate-900 mt-6 mb-4">{line.slice(3)}</h2>;
                    if (line.startsWith('- ')) return <li key={i} className="ml-6 mb-2 list-disc" dangerouslySetInnerHTML={{__html: parsedLine.slice(2)}}/>;
                    if (line.trim() === '') return <div key={i} className="h-4"></div>;
                    return <p key={i} className="mb-4" dangerouslySetInnerHTML={{__html: parsedLine}}></p>;
                  }) : (
                    <div className="text-center text-slate-400 mt-20">No newsletter generated yet.</div>
                  )}
                </div>
              </div>

              {/* Downloads panel */}
              <div className="space-y-6">
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                  <h3 className="font-bold text-slate-900 mb-4">Export Data</h3>
                  <div className="grid grid-cols-1 gap-3">
                    {[
                      { ext: 'csv', label: 'CSV Dataset', color: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
                      { ext: 'xlsx', label: 'Excel Spreadsheet', color: 'bg-green-50 text-green-700 hover:bg-green-100' },
                      { ext: 'json', label: 'Raw JSON', color: 'bg-slate-100 text-slate-700 hover:bg-slate-200' },
                      { ext: 'docx', label: 'Word Document', color: 'bg-blue-50 text-blue-700 hover:bg-blue-100' },
                      { ext: 'pptx', label: 'PowerPoint Deck', color: 'bg-orange-50 text-orange-700 hover:bg-orange-100' },
                    ].map((btn) => (
                      <button
                        key={btn.ext}
                        onClick={() => handleDownload(btn.ext)}
                        className={`w-full flex items-center justify-between px-5 py-4 rounded-xl font-semibold transition-colors ${btn.color}`}
                      >
                        <span className="flex items-center gap-3">
                          <Download className="w-5 h-5" />
                          {btn.label}
                        </span>
                        <span className="uppercase text-xs font-bold opacity-60">.{btn.ext}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          )}
          
        </div>
      </main>
    </div>
  );
}
