import { Activity, ArrowRight, BrainCircuit, Check, Code2, FileCheck2, FileText, FlaskConical, Layers3, LockKeyhole, MessageSquare, Monitor, Search, Server, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ChoiceNote, FlowConnector, IllustrationFrame, IllustrationNode } from './IllustrationElements';

export function HomeIllustration() {
  return <IllustrationFrame name="home" title="Give your idea a place to develop" icon={Layers3}>
    <div className="site-workspace-map"><svg viewBox="0 0 400 260" preserveAspectRatio="none" aria-hidden="true"><path d="M90 40L200 130L310 40 M90 220L200 130L310 220" stroke="currentColor" strokeWidth="1.5" fill="none" strokeDasharray="6 9" className="site-flow-path" /></svg><Link to="/features/research/"><IllustrationNode icon={BrainCircuit} title="Research" detail="Explore a question" /></Link><Link to="/features/builder/"><IllustrationNode icon={SlidersHorizontal} title="Define" detail="Make rules explicit" /></Link><div className="site-map-centre"><span className="site-signal h-2 w-2 rounded-full bg-brand" /><p className="font-semibold">Your trading idea</p><span className="text-xs text-muted-foreground">Your logic. Your decisions.</span></div><Link to="/features/backtesting/"><IllustrationNode icon={FlaskConical} title="Test" detail="Check past behaviour" /></Link><Link to="/features/paper/"><IllustrationNode icon={Activity} title="Practise" detail="Use simulated capital" /></Link></div>
    <Link className="mt-4 flex items-center justify-between rounded-xl border bg-background px-4 py-3 text-sm" to="/features/journal/"><span className="flex items-center gap-2"><FileCheck2 className="h-4 w-4 text-brand" />Review, then refine</span><ArrowRight className="h-4 w-4 text-brand" /></Link>
  </IllustrationFrame>;
}

export function ProductIllustration() {
  return <IllustrationFrame name="product" title="Keep the whole investigation connected" icon={Layers3}>
    <div className="site-product-lanes">{[
      ['Your decisions', BrainCircuit, ['Questions', 'Saved rules']],
      ['Your experiments', FlaskConical, ['Historical tests', 'Paper practice']],
      ['Your review', FileCheck2, ['Recorded results', 'Private notes']],
    ].map(([title, Icon, items]) => <div className="site-product-lane" key={title}><div className="flex items-center gap-2 text-xs font-medium text-brand"><Icon className="h-4 w-4" />{title}</div><div className="mt-3 grid grid-cols-2 gap-2">{items.map(label => <span className="rounded-lg border bg-background px-3 py-3 text-xs" key={label}>{label}</span>)}</div></div>)}</div>
    <ChoiceNote label="What keeps your work connected" choices={[
      ['Context', 'Return to the question, instruments and evidence behind an investigation.'],
      ['Configuration', 'Saved tests and deployments retain the rules and assumptions used.'],
      ['Review', 'Keep Terminal, Paper and activated Private Live records separate.'],
    ]} />
  </IllustrationFrame>;
}

export function ToolkitIllustration() {
  return <IllustrationFrame name="toolkit" title="Start with the task you have" icon={Search}>
    <div className="site-toolkit-tiles">{[[BrainCircuit, 'Investigate', 'Research & screening', '/features/research/'], [SlidersHorizontal, 'Define', 'Rules & saved versions', '/features/builder/'], [Activity, 'Practise', 'Terminal & Paper', '/features/paper/'], [FileText, 'Review', 'Journal & reports', '/features/journal/']].map(([Icon, title, detail, to]) => <Link key={title} to={to} className="site-toolkit-tile"><Icon className="h-6 w-6 text-brand" /><p className="mt-4 text-sm font-semibold">{title}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p><ArrowRight className="mt-3 h-4 w-4 text-brand" /></Link>)}</div>
    <p className="mt-4 text-xs leading-6 text-muted-foreground">Choose a task here or explore the individual tools below.</p>
  </IllustrationFrame>;
}

export function ResearchIntroIllustration() {
  return <IllustrationFrame name="research-intro" title="See what supports an answer" icon={BrainCircuit}>
    <div className="site-research-stack"><IllustrationNode icon={MessageSquare} title="Your question" detail="Stocks, rules or recorded results" /><FlowConnector vertical /><div className="site-research-sources"><div><Layers3 className="h-5 w-5 text-brand" /><span>Relevant context</span></div><div><Search className="h-5 w-5 text-brand" /><span>Calculated evidence</span></div></div><FlowConnector vertical /><IllustrationNode icon={FileCheck2} title="A result you can inspect" detail="Read sources and observation times" /></div>
    <p className="mt-4 text-xs leading-6 text-muted-foreground">Follow up on the same idea. Confirm proposed changes before they happen.</p>
  </IllustrationFrame>;
}

// Previous Live illustration is preserved in the inactive marketing archive.
export function PrivateIllustration() {
  return <IllustrationFrame name="private" title="QuantNest Private" icon={Server}>
    <div className="rounded-2xl border p-6 text-center">
      <Server className="mx-auto h-10 w-10 text-brand" /><p className="mt-5 font-semibold">Not available to customers</p><p className="mt-3 text-sm text-muted-foreground">Research, backtesting and simulation remain available in the public workspace.</p></div>
  </IllustrationFrame>;
}

export function DevelopmentIllustration() {
  return <IllustrationFrame name="development" title="From your specification to useful software" icon={Code2}>
    <div className="site-development-blueprint"><span className="site-blueprint-corner" aria-hidden="true" /><div className="site-blueprint-spec"><Code2 className="h-7 w-7 text-brand" /><p className="mt-3 font-medium">Your requirements</p><p className="mt-1 text-xs text-muted-foreground">A tool for the way you work</p></div><div className="site-blueprint-io">{['Inputs', 'Required behaviour', 'Outputs'].map(label => <span key={label}>{label}</span>)}</div></div>
    <div className="site-delivery-milestones">{['Scope', 'Build', 'Verify', 'Handover'].map((label, index) => <div key={label}><span>0{index + 1}</span><p>{label}</p></div>)}</div>
    <ChoiceNote label="Development deliverables" choices={[
      ['Specification', 'Agree inputs, outputs, environments, ownership and acceptance criteria in writing.'],
      ['Verification', 'Check delivered software against the agreed behaviour at each acceptance milestone.'],
      ['Handover', 'Receive agreed deliverables and choose optional maintenance and support.'],
    ]} />
  </IllustrationFrame>;
}

export function AboutIllustration() {
  return <IllustrationFrame name="about" title="Understand the reasoning" icon={BrainCircuit}>
    <div className="site-about-compass"><svg viewBox="0 0 240 160" aria-hidden="true" className="w-full text-brand"><path d="M120 10L220 80L120 150L20 80Z M120 40L178 80L120 120L62 80Z" fill="none" stroke="currentColor" opacity=".35" /><circle cx="120" cy="80" r="20" fill="currentColor" opacity=".15" /><path d="M120 56V104 M96 80H144" stroke="currentColor" strokeWidth="2" /></svg><p className="text-center text-lg font-semibold">Your decisions. Their context.</p></div>
    <div className="mt-5 flex flex-wrap justify-center gap-2">{['Rules', 'Assumptions', 'Recorded outcomes'].map(label => <span className="rounded-full border bg-background px-3 py-2 text-xs" key={label}>{label}</span>)}</div>
    <p className="mt-5 text-center text-xs leading-6 text-muted-foreground">Software that makes your process easier to inspect.</p>
  </IllustrationFrame>;
}

export function TrustIllustration() {
  return <IllustrationFrame name="trust" title="Clear boundaries, visible context" icon={FileCheck2}>
    <div className="site-trust-layers"><IllustrationNode icon={SlidersHorizontal} title="Rules you choose" detail="Your logic and assumptions" /><IllustrationNode icon={FileCheck2} title="Results you can inspect" detail="Settings, observations and limits" /><IllustrationNode icon={LockKeyhole} title="Choices you control" detail="Sharing and privacy preferences" /></div>
    <p className="mt-5 flex items-start gap-2 text-xs leading-6 text-muted-foreground"><Check className="mt-1 h-4 w-4 shrink-0 text-brand" />Understand the software before choosing a plan or installation.</p>
  </IllustrationFrame>;
}

export function SecurityIllustration() {
  return <IllustrationFrame name="security" title="Protect access. Report concerns." icon={ShieldCheck}>
    <div className="site-security-boundary"><LockKeyhole className="h-12 w-12 text-brand" /><div><p className="font-semibold">Your account access</p><p className="mt-2 text-xs leading-6 text-muted-foreground">Password + second verification step</p></div></div>
    <div className="site-security-devices"><span><Monitor className="h-4 w-4 text-brand" />Review sign-ins</span><span><ShieldCheck className="h-4 w-4 text-brand" />Keep recovery codes private</span></div>
    <ChoiceNote label="Security help" choices={[
      ['Protect', 'Enable two-factor authentication and revoke sign-in sessions you do not recognise.'],
      ['Report', 'Send a security concern through Contact, without passwords, tokens or other people’s data.'],
      ['Project access', 'Agree support access and responsibilities for custom work.'],
    ]} />
  </IllustrationFrame>;
}
