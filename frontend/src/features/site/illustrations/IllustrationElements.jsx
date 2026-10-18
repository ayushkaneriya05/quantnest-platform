import { useId, useState } from 'react';
import PropTypes from 'prop-types';

export function IllustrationFrame({ name, title, icon: Icon, children, caption }) {
  return <figure data-illustration={name} className={`site-figure site-illustration-${name}`} aria-label={title}>
    <div className="site-illustration-heading"><span className="site-eyebrow">{title}</span><Icon className="h-5 w-5 shrink-0 text-brand" aria-hidden="true" /></div>
    {children}
    {caption && <figcaption className="mt-4 text-xs leading-6 text-muted-foreground">{caption}</figcaption>}
  </figure>;
}
IllustrationFrame.propTypes = { name: PropTypes.string.isRequired, title: PropTypes.string.isRequired, icon: PropTypes.elementType.isRequired, children: PropTypes.node.isRequired, caption: PropTypes.string };

export function ChoiceNote({ label, choices }) {
  const [selected, setSelected] = useState(0);
  const id = useId();
  return <div className="site-choice-note"><div role="group" aria-label={label} className="flex flex-wrap gap-2">{choices.map(([title], index) => <button type="button" key={title} aria-pressed={selected === index} aria-controls={id} onClick={() => setSelected(index)} className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring ${selected === index ? 'border-brand/40 bg-brand/10 text-brand' : 'bg-background text-muted-foreground hover:text-foreground'}`}>{title}</button>)}</div><p id={id} aria-live="polite" className="mt-3 min-h-12 text-xs leading-6 text-muted-foreground">{choices[selected][1]}</p></div>;
}
ChoiceNote.propTypes = { label: PropTypes.string.isRequired, choices: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.string)).isRequired };

export function IllustrationNode({ icon: Icon, title, detail, className = '' }) {
  return <div className={`site-illustration-node ${className}`}><span className="site-node-icon"><Icon className="h-5 w-5" aria-hidden="true" /></span><div className="min-w-0"><p className="text-sm font-medium">{title}</p>{detail && <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>}</div></div>;
}
IllustrationNode.propTypes = { icon: PropTypes.elementType.isRequired, title: PropTypes.string.isRequired, detail: PropTypes.string, className: PropTypes.string };

export function FlowConnector({ vertical = false }) {
  return <div className={`site-flow-connector ${vertical ? 'site-flow-vertical' : ''}`} aria-hidden="true"><span /></div>;
}
FlowConnector.propTypes = { vertical: PropTypes.bool };
