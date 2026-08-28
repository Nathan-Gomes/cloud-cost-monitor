import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowDownRight, ArrowUpRight, Boxes, CheckCircle2,
  ChevronDown, CircleDollarSign, Cloud, Database, Gauge, HardDrive,
  LayoutDashboard, Menu, RefreshCw, Search, Server, ShieldCheck, Sparkles,
  WalletCards, X,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import './App.css'

type Severity = 'critical' | 'high' | 'medium' | 'low'
type Finding = { id: string; severity: Severity; finding_type: string; title: string; resource_id: string | null; service: string; region: string; detected_at: string; monthly_impact: number; evidence: string; recommendation: string; status: string }
type Resource = { resource_id: string; name: string; resource_type: string; service: string; region: string; state: string; monthly_cost: number; utilization_pct: number | null; attached_to: string | null; age_days: number; tags: Record<string, string>; collected_at: string }
type DashboardData = {
  meta: { generated_at: string; mode: string; period: string }
  summary: { current_month_cost: number; forecast_cost: number; monthly_budget: number; change_pct: number; potential_savings: number; active_findings: number; monitored_resources: number }
  cost_series: Array<Record<string, string | number>>
  service_breakdown: Array<{ service: string; cost: number; share: number }>
  findings: Finding[]
  resources: Resource[]
}

const serviceColors = ['#166f62', '#3478a5', '#d38b31', '#8064a2', '#c6534f', '#6f7b85']
const money = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 })

function App() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [mobileNav, setMobileNav] = useState(false)
  const [findingFilter, setFindingFilter] = useState<'all' | Severity>('all')
  const [resourceQuery, setResourceQuery] = useState('')
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)

  const loadData = async () => {
    const apiUrl = import.meta.env.VITE_API_URL
    try {
      const demoUrl = `${import.meta.env.BASE_URL}demo-data.json`
      const response = await fetch(apiUrl ? `${apiUrl}/api/dashboard` : demoUrl)
      if (!response.ok) throw new Error('Dashboard data unavailable')
      setData(await response.json())
    } catch {
      const fallback = await fetch(`${import.meta.env.BASE_URL}demo-data.json`)
      setData(await fallback.json())
    } finally {
      setLoading(false)
    }
  }

  const refreshData = () => {
    setLoading(true)
    void loadData()
  }

  const acknowledgeSelected = () => {
    if (!selectedFinding) return
    setData((current) => current ? {
      ...current,
      summary: {
        ...current.summary,
        active_findings: Math.max(0, current.summary.active_findings - 1),
        potential_savings: Math.max(0, current.summary.potential_savings - selectedFinding.monthly_impact),
      },
      findings: current.findings.map((finding) => finding.id === selectedFinding.id ? { ...finding, status: 'acknowledged' } : finding),
    } : current)
    setSelectedFinding(null)
  }

  // The initial collection is an external synchronization by design.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void loadData() }, [])

  const visibleFindings = useMemo(
    () => data?.findings.filter((finding) => finding.status === 'open' && (findingFilter === 'all' || finding.severity === findingFilter)) ?? [],
    [data, findingFilter],
  )
  const visibleResources = useMemo(() => {
    const query = resourceQuery.trim().toLowerCase()
    if (!query) return data?.resources ?? []
    return (data?.resources ?? []).filter((resource) =>
      [resource.name, resource.resource_id, resource.service, resource.region, resource.tags.Owner]
        .filter(Boolean).some((value) => value.toLowerCase().includes(query)),
    )
  }, [data, resourceQuery])

  if (!data) return <div className="loading-screen"><Cloud size={30} /><span>{loading ? 'Loading cloud inventory' : 'No monitoring data available'}</span></div>

  const chartData = data.cost_series.slice(-30).map((point) => ({
    ...point,
    label: new Date(`${point.date}T12:00:00`).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }),
  }))
  const budgetUsed = (data.summary.forecast_cost / data.summary.monthly_budget) * 100
  const budgetBarWidth = Math.min(budgetUsed, 100)

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand"><span className="brand-mark"><Gauge size={20} /></span><div><strong>CostScope</strong><small>Cloud FinOps</small></div></div>
        <button className="sidebar-close" type="button" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={20} /></button>
        <nav aria-label="Primary navigation">
          <a className="nav-item active" href="#overview"><LayoutDashboard size={18} /><span>Overview</span></a>
          <a className="nav-item" href="#findings"><AlertTriangle size={18} /><span>Findings</span><b>{data.summary.active_findings}</b></a>
          <a className="nav-item" href="#resources"><Boxes size={18} /><span>Resources</span></a>
          <a className="nav-item" href="#budget"><WalletCards size={18} /><span>Budget</span></a>
        </nav>
        <div className="sidebar-section"><p>MONITORED ACCOUNT</p><div className="account-picker"><span><Cloud size={16} />Operations</span><ChevronDown size={15} /></div></div>
        <div className="collector-status"><span><CheckCircle2 size={16} /></span><div><strong>Collector healthy</strong><small>Daily at 06:00 UTC</small></div></div>
        <div className="sidebar-footer"><ShieldCheck size={16} /><span>Read-only AWS access</span></div>
      </aside>
      {mobileNav && <button className="sidebar-scrim" type="button" onClick={() => setMobileNav(false)} aria-label="Close navigation overlay" />}

      <main className="main-content" id="overview">
        <header className="topbar">
          <button className="icon-button menu-button" type="button" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div><p className="eyebrow">FINOPS OVERVIEW</p><h1>Cloud cost monitor</h1></div>
          <div className="topbar-actions">
            <div className="sync-meta"><span className="live-dot" /><div><strong>{data.meta.mode === 'demo' ? 'Demo workspace' : 'AWS connected'}</strong><small>Updated {relativeTime(data.meta.generated_at)}</small></div></div>
            <button className="refresh-button" type="button" onClick={refreshData} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} />Refresh</button>
          </div>
        </header>

        <section className="workspace-status">
          <div><Sparkles size={17} /><p><strong>{data.summary.active_findings} optimization opportunities</strong> could reduce the current run rate by approximately <strong>{money.format(data.summary.potential_savings)} per month.</strong></p></div>
          <a href="#findings">Review findings <ArrowDownRight size={15} /></a>
        </section>

        <section className="kpi-grid" aria-label="Cost summary">
          <Metric label="Month-to-date" value={money.format(data.summary.current_month_cost)} detail={`${signed(data.summary.change_pct)} vs. prior period`} tone={data.summary.change_pct > 0 ? 'danger' : 'good'} icon={<CircleDollarSign size={18} />} />
          <Metric label="Month forecast" value={money.format(data.summary.forecast_cost)} detail={`${budgetUsed.toFixed(0)}% of ${money.format(data.summary.monthly_budget)} budget`} tone={budgetUsed > 90 ? 'warning' : 'neutral'} icon={<Gauge size={18} />} />
          <Metric label="Savings potential" value={money.format(data.summary.potential_savings)} detail="Monthly run-rate estimate" tone="good" icon={<Sparkles size={18} />} />
          <Metric label="Resources monitored" value={String(data.summary.monitored_resources)} detail={`${data.summary.active_findings} require review`} tone="neutral" icon={<Boxes size={18} />} />
        </section>

        <section className="analytics-grid">
          <article className="panel trend-panel">
            <div className="panel-header"><div><p className="eyebrow">SPEND TREND</p><h2>Daily cloud cost</h2></div><span className="period-chip">Last 30 days</span></div>
            <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 10, right: 8, left: -16, bottom: 0 }}><defs><linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#166f62" stopOpacity={0.24} /><stop offset="100%" stopColor="#166f62" stopOpacity={0.02} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#e8e9e7" strokeDasharray="3 3" /><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: '#777d79', fontSize: 11 }} minTickGap={28} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#777d79', fontSize: 11 }} tickFormatter={(value) => `$${value}`} /><Tooltip content={<CostTooltip />} /><Area type="monotone" dataKey="total" stroke="#166f62" strokeWidth={2} fill="url(#costFill)" dot={false} activeDot={{ r: 4, fill: '#166f62', stroke: '#fff', strokeWidth: 2 }} /></AreaChart></ResponsiveContainer></div>
          </article>

          <article className="panel service-panel">
            <div className="panel-header"><div><p className="eyebrow">ALLOCATION</p><h2>Cost by service</h2></div></div>
            <div className="service-visual">
              <div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.service_breakdown} dataKey="cost" nameKey="service" innerRadius={52} outerRadius={72} paddingAngle={2} stroke="none">{data.service_breakdown.map((entry, index) => <Cell key={entry.service} fill={serviceColors[index % serviceColors.length]} />)}</Pie><Tooltip formatter={(value) => money.format(Number(value))} /></PieChart></ResponsiveContainer><div className="donut-center"><strong>{money.format(data.summary.current_month_cost)}</strong><span>month to date</span></div></div>
              <div className="service-list">{data.service_breakdown.slice(0, 5).map((service, index) => <div className="service-row" key={service.service}><span className="legend-dot" style={{ backgroundColor: serviceColors[index % serviceColors.length] }} /><div><strong>{service.service.replace('Amazon ', '').replace('AWS ', '')}</strong><small>{service.share}% of spend</small></div><b>{money.format(service.cost)}</b></div>)}</div>
            </div>
          </article>
        </section>

        <section className="panel findings-panel" id="findings">
          <div className="panel-header findings-heading"><div><p className="eyebrow">ACTION QUEUE</p><h2>Optimization findings</h2><p className="panel-subtitle">Prioritized from cost, utilization, attachment state, and resource age.</p></div><div className="filter-group" aria-label="Filter findings">{(['all', 'critical', 'high', 'medium', 'low'] as const).map((filter) => <button type="button" key={filter} className={findingFilter === filter ? 'selected' : ''} onClick={() => setFindingFilter(filter)}>{filter}</button>)}</div></div>
          <div className="findings-table table-scroll"><table><thead><tr><th>Severity</th><th>Finding</th><th>Resource</th><th>Evidence</th><th>Monthly impact</th><th aria-label="Open finding" /></tr></thead><tbody>{visibleFindings.map((finding) => <tr key={finding.id} onClick={() => setSelectedFinding(finding)}><td><span className={`severity severity-${finding.severity}`}>{finding.severity}</span></td><td><strong>{finding.title}</strong><small>{finding.service} · {finding.region}</small></td><td><code>{finding.resource_id ?? 'account-level'}</code></td><td><span className="evidence-cell">{finding.evidence}</span></td><td><strong>{money.format(finding.monthly_impact)}</strong></td><td><button className="table-action" type="button" aria-label={`Open ${finding.title}`}><ArrowUpRight size={16} /></button></td></tr>)}</tbody></table></div>
        </section>

        <section className="panel resources-panel" id="resources">
          <div className="panel-header resources-heading"><div><p className="eyebrow">INVENTORY</p><h2>Monitored resources</h2></div><label className="search-box"><Search size={17} /><input value={resourceQuery} onChange={(event) => setResourceQuery(event.target.value)} placeholder="Search resources" aria-label="Search resources" /></label></div>
          <div className="resource-grid">{visibleResources.map((resource) => <article className="resource-item" key={resource.resource_id}><span className="resource-icon">{resourceIcon(resource.resource_type)}</span><div className="resource-main"><div><strong>{resource.name}</strong><code>{resource.resource_id}</code></div><small>{resource.resource_type} · {resource.region}</small></div><div className="resource-util"><span>{resource.utilization_pct == null ? resource.state : `${resource.utilization_pct.toFixed(1)}% util.`}</span><b>{money.format(resource.monthly_cost)}/mo</b></div></article>)}</div>
        </section>

        <section className="budget-band" id="budget">
          <div><p className="eyebrow">MONTHLY BUDGET</p><h2>{money.format(data.summary.forecast_cost)} forecast against {money.format(data.summary.monthly_budget)}</h2></div>
          <div className="budget-progress"><div><span>Forecast consumption</span><strong>{budgetUsed.toFixed(0)}%</strong></div><div className="progress-track"><span style={{ width: `${budgetBarWidth}%` }} /></div><p>{data.summary.forecast_cost > data.summary.monthly_budget ? `${money.format(data.summary.forecast_cost - data.summary.monthly_budget)} above the budget threshold.` : `${money.format(data.summary.monthly_budget - data.summary.forecast_cost)} remaining before the budget threshold.`}</p></div>
        </section>
      </main>

      {selectedFinding && <div className="drawer-layer"><button className="drawer-scrim" type="button" onClick={() => setSelectedFinding(null)} aria-label="Close finding details" /><aside className="finding-drawer" aria-label="Finding details"><div className="drawer-header"><div><span className={`severity severity-${selectedFinding.severity}`}>{selectedFinding.severity}</span><h2>{selectedFinding.title}</h2></div><button className="icon-button" type="button" onClick={() => setSelectedFinding(null)} aria-label="Close"><X size={19} /></button></div><dl><div><dt>Resource</dt><dd><code>{selectedFinding.resource_id ?? 'Account-level'}</code></dd></div><div><dt>Estimated impact</dt><dd>{money.format(selectedFinding.monthly_impact)} per month</dd></div><div><dt>Region</dt><dd>{selectedFinding.region}</dd></div></dl><section><p className="eyebrow">EVIDENCE</p><p>{selectedFinding.evidence}</p></section><section className="recommendation"><p className="eyebrow">RECOMMENDED ACTION</p><p>{selectedFinding.recommendation}</p></section><div className="drawer-note"><ShieldCheck size={17} /><p>This monitor is read-only. Any resource change requires review in the cloud console or infrastructure code.</p></div><button className="primary-button" type="button" onClick={acknowledgeSelected}><CheckCircle2 size={17} />Acknowledge finding</button></aside></div>}
    </div>
  )
}

function Metric({ label, value, detail, tone, icon }: { label: string; value: string; detail: string; tone: string; icon: React.ReactNode }) {
  return <article className="metric"><div className="metric-label"><span>{icon}</span><p>{label}</p></div><strong>{value}</strong><div className={`metric-detail tone-${tone}`}>{tone === 'danger' ? <ArrowUpRight size={14} /> : tone === 'good' ? <ArrowDownRight size={14} /> : null}<span>{detail}</span></div></article>
}

function CostTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><span>{label}</span><strong>{money.format(payload[0].value)}</strong></div>
}

function signed(value: number) { return `${value > 0 ? '+' : ''}${value.toFixed(1)}%` }
function relativeTime(iso: string) { const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000)); return minutes < 2 ? 'just now' : `${minutes} min ago` }
function resourceIcon(type: string) { if (type.includes('EC2')) return <Server size={18} />; if (type.includes('RDS')) return <Database size={18} />; if (type.includes('EBS')) return <HardDrive size={18} />; return <Cloud size={18} /> }

export default App
