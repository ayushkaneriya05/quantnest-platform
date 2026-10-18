import { Activity, ArrowRight, BookOpen, BrainCircuit, Check, CircleDot, Clock3, FileCheck2, FileText, Filter, FlaskConical, History, Layers3, LineChart, ListChecks, Monitor, Search, ShieldCheck, SlidersHorizontal, Terminal, Wallet } from 'lucide-react';
import { ChoiceNote, FlowConnector, IllustrationFrame, IllustrationNode } from './IllustrationElements';

export function ResearchIllustration() {
  return <IllustrationFrame name="research" title="Investigate in a conversation" icon={BrainCircuit}>
    <div className="site-research-prompt">How do these stocks differ in momentum and volatility?</div>
    <div className="site-research-evidence"><BrainCircuit className="h-5 w-5 shrink-0 text-brand" /><div><p className="text-sm font-medium">Understand the supporting evidence</p><div className="mt-3 grid grid-cols-2 gap-2">{[['Calculations', 'Indicator values'], ['Sources', 'Observation times']].map(([label, text]) => <div className="rounded-xl border bg-background p-3" key={label}><p className="text-xs font-medium text-brand">{label}</p><p className="mt-1 text-xs text-muted-foreground">{text}</p></div>)}</div></div></div>
    <ChoiceNote label="Research workflow" choices={[
      ['Ask', 'Start with a question. Attach stocks, a strategy or your recorded results when useful.'],
      ['Inspect', 'Open citations and check the calculations, timeframe and observation date.'],
      ['Refine', 'Continue the conversation or review a proposed draft. Persistent changes require your confirmation.'],
    ]} />
  </IllustrationFrame>;
}

export function ScreenerIllustration() {
  return <IllustrationFrame name="screener" title="Your stocks. Your filters." icon={Filter}>
    <div className="site-screen-universe"><Search className="h-5 w-5 text-brand" /><span className="text-sm">Your selected stocks or watchlist</span></div>
    <div className="site-screen-filters">{['Price', 'Trend', 'Momentum'].map(label => <span key={label} className="rounded-full border bg-background px-3 py-2 text-xs">{label}</span>)}</div>
    <div className="site-screen-result"><div className="site-screen-sweep" aria-hidden="true" /><div className="grid grid-cols-3 gap-2 border-b pb-3 text-xs font-medium text-brand"><span>Condition</span><span>Values</span><span>Candle time</span></div>{['Inspect why a stock matches', 'Review excluded stocks'].map(label => <div key={label} className="flex items-center gap-3 border-b py-3 text-xs text-muted-foreground"><ListChecks className="h-4 w-4 text-brand" />{label}</div>)}</div>
    <ChoiceNote label="How screening conditions combine" choices={[
      ['All conditions', 'AND requires every chosen condition to pass at the recorded observation.'],
      ['Any condition', 'OR requires at least one chosen condition to pass. A match is not a trading recommendation.'],
    ]} />
  </IllustrationFrame>;
}

export function BuilderIllustration() {
  return <IllustrationFrame name="builder" title="Build a readable rule set" icon={SlidersHorizontal}>
    <div className="site-rule-tree"><div className="site-rule-junction">ENTRY</div><div className="site-rule-branches"><div><CircleDot className="h-4 w-4 text-brand" />Your price condition</div><div><CircleDot className="h-4 w-4 text-brand" />Your indicator condition</div></div></div>
    <div className="site-builder-settings"><IllustrationNode icon={Wallet} title="Position size" detail="Fixed or capital-based" /><IllustrationNode icon={SlidersHorizontal} title="Exit settings" detail="Rules, stop-loss, target" /></div>
    <div className="site-version-strip"><History className="h-4 w-4 text-brand" /><span>Save your rules</span><ArrowRight className="h-4 w-4" /><span>Add version notes</span></div>
    <ChoiceNote label="Strategy configuration sections" choices={[
      ['Conditions', 'Choose indicator inputs, operators, parameters and AND/OR groups for your idea.'],
      ['Safeguards', 'Describe trading windows, cooldown and auto-disable rules as part of the saved configuration.'],
      ['Versions', 'Inspect readable changes before testing or deploying a selected saved version.'],
    ]} />
  </IllustrationFrame>;
}

export function BacktestIllustration() {
  return <IllustrationFrame name="backtesting" title="One test. Recorded assumptions." icon={FlaskConical}>
    <div className="site-test-window"><div className="flex items-center justify-between gap-3 border-b pb-3 text-xs text-muted-foreground"><span>Your selected historical period</span><Clock3 className="h-4 w-4 text-brand" /></div><div className="site-history-bars" aria-hidden="true">{[35, 60, 45, 80, 55, 75, 40, 65, 85, 50, 70, 45].map((height, index) => <span key={index} style={{ height: `${height}%`, '--figure-delay': `${index * .07}s` }} />)}</div><p className="text-xs text-muted-foreground">Saved rules + capital + costs + slippage</p></div>
    <div className="site-test-outputs">{[[ListChecks, 'Trades'], [Wallet, 'Costs'], [LineChart, 'Drawdown']].map(([Icon, label]) => <div key={label}><Icon className="h-5 w-5 text-brand" /><span>{label}</span></div>)}</div>
    <ChoiceNote label="What to inspect in a backtest" choices={[
      ['Results', 'Read recorded trades and performance with the settings and coverage used for that test.'],
      ['Diagnostics', 'Use available entry diagnostics to investigate a test with no trades.'],
      ['Compare', 'Compare saved settings and assumptions before comparing two test results.'],
    ]} />
  </IllustrationFrame>;
}

export function TerminalIllustration() {
  return <IllustrationFrame name="terminal" title="Your manual practice desk" icon={Terminal} caption="A separate simulated account. No real broker orders.">
    <div className="site-terminal-desk"><div className="site-terminal-chart"><p className="text-xs text-muted-foreground">Your selected stock</p><svg viewBox="0 0 200 145" aria-hidden="true" className="my-3 w-full text-brand"><path d="M0 35H200 M0 80H200 M0 125H200" stroke="currentColor" opacity=".12" />{[72, 60, 84, 45, 55, 38, 70].map((height, index) => <g key={index} className="site-chart-candle" style={{ '--figure-delay': `${index * .1}s` }}><path d={`M${20 + index * 26} ${height - 20}V${height + 45}`} stroke="currentColor" /><rect x={14 + index * 26} y={height} width="12" height="23" rx="1" fill="currentColor" opacity={index % 2 ? '.45' : '.8'} /></g>)}</svg><span className="text-xs text-muted-foreground">Watchlist · chart · timeframe</span></div><div className="site-terminal-ticket"><p className="mb-4 text-xs font-medium text-brand">Order review</p>{['Side', 'Quantity', 'Order type', 'Relevant price'].map(label => <p className="border-b py-2 text-xs text-muted-foreground" key={label}>{label}</p>)}<div className="mt-4 flex items-center gap-2 text-xs"><Check className="h-4 w-4 text-brand" />You confirm</div></div></div>
    <ChoiceNote label="Manual trading workflow" choices={[
      ['Inspect', 'Choose your stock and timeframe and inspect the available chart observations.'],
      ['Practise', 'Review a supported simulated order. Modify or cancel eligible pending orders.'],
      ['Review', 'Follow Terminal positions and recorded closes separately from automated Paper.'],
    ]} />
  </IllustrationFrame>;
}

export function PaperIllustration() {
  return <IllustrationFrame name="paper" title="Your strategy, in Paper" icon={Activity}>
    <div className="site-paper-allocation"><div className="site-paper-ring"><Wallet className="h-7 w-7 text-brand" /></div><div><p className="text-sm font-medium">Simulated capital</p><p className="mt-1 text-xs text-muted-foreground">Allocated to your saved version</p></div></div>
    <div className="site-paper-execution"><IllustrationNode icon={Layers3} title="Selected version" detail="Your approved rules" /><FlowConnector vertical /><IllustrationNode icon={Activity} title="Simulated execution" detail="Orders → positions → recorded closes" /></div>
    <ChoiceNote label="Paper session controls explained" choices={[
      ['Monitor', 'Follow the session, costs, orders and positions in its separate Paper account.'],
      ['Pause', 'Prevent new entries. Protective behaviour and existing exposure remain separate considerations.'],
      ['Stop', 'Stop explicitly and inspect remaining positions or orders that need settlement.'],
    ]} />
  </IllustrationFrame>;
}

export function JournalIllustration() {
  return <IllustrationFrame name="journal" title="A record you can learn from" icon={BookOpen}>
    <div className="site-journal-pages"><div className="site-journal-binding" aria-hidden="true" /><div className="site-journal-note"><FileText className="h-5 w-5 text-brand" /><p className="mt-3 text-sm font-medium">Your trade review</p>{['Decision context', 'Mistakes & lessons', 'Next investigation'].map(label => <p key={label} className="border-b py-3 text-xs text-muted-foreground">{label}</p>)}</div><div className="site-journal-report"><LineChart className="h-5 w-5 text-brand" /><p className="mt-3 text-sm font-medium">Source-specific report</p><div className="mt-5 space-y-3">{['Recorded closes', 'Realised P&L', 'Available charges'].map(label => <span key={label} className="block rounded-lg border bg-background p-2 text-xs text-muted-foreground">{label}</span>)}</div></div></div>
    <ChoiceNote label="Keep execution sources separate" choices={[
      ['Terminal', 'Review your manual simulation decisions in the Terminal source.'],
      ['Paper', 'Review automated strategy simulation in the Paper source.'],
      ['Private Live', 'An activated Private installation can review recorded broker execution separately.'],
    ]} />
  </IllustrationFrame>;
}

export function ControlsIllustration() {
  return <IllustrationFrame name="controls" title="Your account and activity" icon={ShieldCheck}>
    <div className="site-account-shield"><ShieldCheck className="h-11 w-11 text-brand" /><div><p className="text-sm font-medium">Protect workspace access</p><p className="mt-1 text-xs text-muted-foreground">Security · sign-in sessions · history</p></div></div>
    <div className="site-account-controls"><IllustrationNode icon={Monitor} title="Sign-in sessions" detail="Inspect and revoke access" /><IllustrationNode icon={History} title="Activity records" detail="Review account and strategy changes" /><IllustrationNode icon={FileCheck2} title="Saved versions" detail="Know which rules are in use" /></div>
    <ChoiceNote label="Account controls explained" choices={[
      ['2FA', 'Add a second verification step and keep recovery codes private.'],
      ['Sessions', 'Review active sign-ins and revoke access you no longer recognise.'],
      ['Activity', 'Inspect recorded changes and explicit account or deployment actions.'],
    ]} />
  </IllustrationFrame>;
}
