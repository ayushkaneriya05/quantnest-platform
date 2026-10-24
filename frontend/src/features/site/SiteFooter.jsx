import { Link } from 'react-router-dom';
import { usePlatform } from '@/shared/context/platform';

const groups = {
  Workspace: [['Product', '/product/'], ['All features', '/features/'], ['Pricing', '/pricing/'], ['Documentation', '/docs/'], ['FAQ', '/faq/']],
  Company: [['About', '/about/'], ['Custom development', '/custom-development/'], ['Private availability', '/private/'], ['Contact & support', '/contact/'], ['Feedback', '/feedback/'], ['Changelog', '/changelog/'], ['Status', '/status/']],
  Trust: [['Trust centre', '/trust/'], ['Privacy', '/privacy-policy'], ['Terms', '/terms-of-service'], ['Refunds', '/refunds/'], ['Simulation & data', '/methodology/'], ['Security', '/security/']],
};
export default function SiteFooter() {
  const { catalog } = usePlatform();
  const contact = catalog?.contact;
  return <footer className="border-t bg-background"><div className="mx-auto w-[calc(100%_-_2rem)] max-w-7xl py-8">
    <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr]">
      <div><Link to="/" aria-label="QuantNest home"><img src="/logo_1-wordmark.png" alt="QuantNest" className="h-10 w-auto" /></Link><p className="my-5 max-w-sm text-sm leading-7 text-muted-foreground">Software for your own logic. Research, testing, simulation and review in one connected workspace.</p>{contact && <><a href={`mailto:${contact.email}`} className="break-all text-sm text-brand">{contact.email}</a><p className="mt-3 text-xs leading-6 text-muted-foreground">{contact.hours}</p></>}</div>
      {Object.entries(groups).map(([title, links]) => <nav key={title} aria-label={title}><h2 className="mb-4 text-sm font-semibold">{title}</h2><ul className="space-y-3">{links.map(([label, href]) => <li key={href}><Link className="text-sm text-muted-foreground transition-colors hover:text-brand" to={href}>{label}</Link></li>)}</ul></nav>)}
    </div><div className="mt-10 border-t pt-6 text-xs leading-6 text-muted-foreground"><p>QuantNest provides software, not investment advice or assured returns. Backtest and Paper results are simulations. Public plans cover simulation through Paper. Customer Live trading and Private deployments are not currently offered.</p>{contact && <p className="mt-3">© {new Date().getFullYear()} {contact.name}. All rights reserved.</p>}</div>
  </div></footer>;
}
