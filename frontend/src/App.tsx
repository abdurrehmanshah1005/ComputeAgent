import { FormEvent, useCallback, useEffect, useState } from 'react'
import './App.css'

type ExecutionStatus = 'queued' | 'success' | 'error'
type Artifact = { filename: string; download_url: string }
type Execution = { execution_id: string; prompt: string; status: ExecutionStatus; output_logs: string; created_at: string; artifacts: Artifact[] }
const statusLabels: Record<ExecutionStatus, string> = { queued: 'In queue', success: 'Completed', error: 'Failed' }

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [prompt, setPrompt] = useState('')
  const [executions, setExecutions] = useState<Execution[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadExecutions = useCallback(async () => {
    try {
      const response = await fetch('/api/executions')
      if (!response.ok) throw new Error()
      setExecutions(await response.json() as Execution[])
      setError('')
    } catch { setError('The execution feed is unavailable right now.') }
    finally { setIsLoading(false) }
  }, [])

  useEffect(() => {
    void loadExecutions()
    const interval = window.setInterval(() => void loadExecutions(), 3000)
    return () => window.clearInterval(interval)
  }, [loadExecutions])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file || !prompt.trim()) { setError('Choose a data file and describe the analysis to run.'); return }
    setIsSubmitting(true); setError('')
    const formData = new FormData(); formData.append('file', file); formData.append('prompt', prompt.trim())
    try {
      const response = await fetch('/api/analyze', { method: 'POST', body: formData })
      if (!response.ok) throw new Error()
      setPrompt(''); setFile(null)
      const input = document.getElementById('data-file') as HTMLInputElement | null
      if (input) input.value = ''
      await loadExecutions()
    } catch { setError('Analysis could not be queued. Check the backend and try again.') }
    finally { setIsSubmitting(false) }
  }

  return (
    <div className="app-shell">
      <header className="topbar"><a className="brand" href="/" aria-label="ComputeAgent home"><span className="brand-mark">C</span><span>ComputeAgent</span></a><span className="system-status"><span className="status-dot" />System online</span></header>
      <main className="dashboard">
        <section className="intro"><div><p className="eyebrow">Workspace / Analysis lab</p><h1>Turn raw data into<br /><em>clear decisions.</em></h1><p className="intro-copy">Upload a dataset and let your analysis agent explore, explain, and visualize what matters.</p></div><div className="run-count"><strong>{executions.length.toString().padStart(2, '0')}</strong><span>runs<br />this workspace</span></div></section>
        <div className="workspace-grid">
          <aside className="input-panel"><div className="panel-heading"><div><p className="eyebrow">New analysis</p><h2>Start a run</h2></div><span className="step-label">01</span></div>
            <form onSubmit={handleSubmit}><label className="field-label" htmlFor="data-file">Dataset</label><label className={`drop-zone${file ? ' has-file' : ''}`} htmlFor="data-file"><span className="upload-icon">↑</span><span>{file ? file.name : 'Drop CSV or Excel file here'}</span><small>{file ? `${(file.size / 1024).toFixed(1)} KB ready` : 'or click to browse'}</small><input id="data-file" type="file" accept=".csv,.xls,.xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label><label className="field-label" htmlFor="analysis-prompt">Your question</label><textarea id="analysis-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="What should we discover?" rows={5} />{error && <p className="error-message" role="alert">{error}</p>}<button className="submit-button" type="submit" disabled={isSubmitting}>{isSubmitting ? 'Queuing analysis...' : 'Run analysis'} <span aria-hidden="true">↗</span></button></form>
            <p className="privacy-note">Your files stay inside this workspace.</p>
          </aside>
          <section className="feed-panel" aria-labelledby="feed-title"><div className="feed-heading"><div><p className="eyebrow">Live activity</p><h2 id="feed-title">Execution feed</h2></div><span className="refresh-note"><span className="pulse-dot" />Updating every 3 sec</span></div>{isLoading ? <div className="empty-state">Loading your workspace...</div> : executions.length === 0 ? <div className="empty-state"><span className="empty-mark">—</span><strong>No runs yet</strong><span>Your completed analyses will appear here.</span></div> : <div className="execution-list">{executions.map((execution) => <ExecutionCard key={execution.execution_id} execution={execution} />)}</div>}</section>
        </div>
      </main><footer><span>COMPUTEAGENT <b>·</b> DATA ANALYSIS PLATFORM</span><span>v1.0</span></footer>
    </div>
  )
}

function ExecutionCard({ execution }: { execution: Execution }) {
  const date = new Date(execution.created_at)
  return <article className="execution-card"><div className="execution-top"><span className={`status-badge ${execution.status}`}><span />{statusLabels[execution.status]}</span><time dateTime={execution.created_at}>{date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} · {date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}</time></div><p className="execution-prompt">{execution.prompt}</p>{execution.output_logs && <pre className="output-logs">{execution.output_logs}</pre>}{execution.artifacts?.length > 0 && <div className="artifacts">{execution.artifacts.map((artifact) => <a className="artifact" href={artifact.download_url} target="_blank" rel="noreferrer" key={artifact.download_url}>{artifact.filename.toLowerCase().endsWith('.png') && <img src={artifact.download_url} alt={artifact.filename} />}<span>{artifact.filename}</span><span aria-hidden="true">↓</span></a>)}</div>}</article>
}

export default App
