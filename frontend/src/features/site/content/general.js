export const generalPages = {
  product: { title: 'One workspace. A clearer trading process.', description: 'Move from a question to explicit rules, historical tests and simulated practice. Keep the context behind every result.', sections: [
    ['Research an idea', ['Ask AI about selected stocks or your own strategy question.', 'Screen your watchlist with conditions you choose, then investigate the matching results.']],
    ['Define your rules', ['Build entries, exits, sizing and safeguards in the visual strategy builder.', 'Save versions with notes so you know exactly what changed between experiments.']],
    ['Test and practise', ['Backtest a saved configuration with dates, capital and costs you can inspect.', 'Practise manually in Terminal or automatically in Paper, then review what was recorded.']],
    ['Keep environments clear', ['Public subscriptions include the supported workflow through simulation and Paper trading.', 'Customer Live trading and Private deployments are not currently offered. Build and Pro list NSE futures and options as coming soon. They are not available yet; current public workflows support NSE stocks.']],
  ] },
  // Previous customer offer: docs/archive/private-marketing-2026-10-23.md.
  private: { title: 'QuantNest Private', description: 'Not currently available to customers. Public subscriptions support research, backtesting and simulated trading.', sections: [
    ['Current availability', ['QuantNest Private is not available for purchase. Customer Live trading is not currently offered.', 'Any future customer deployment will be announced separately after its supported scope and applicable requirements are established.']],
    ['What you can use today', ['Use the public workspace to research ideas, define rules, backtest and practise with simulated capital.', 'Custom Development is a separate project service for applications, tools and integrations built to agreed requirements.']],
  ], cta: 'Ask a question', kind: 'general' },
  'custom-development': { title: 'Software built around your way of working.', description: 'Tell us what you want to achieve. We help define the requirements, build and test the agreed software, and hand it over with documentation. No technical specification is needed to start.', sections: [
    ['Who we can help', ['Individuals and businesses needing custom applications, internal tools, dashboards or workflow automation. Trading and research tools can also be scoped.', 'This is a separate project service. Your project does not need to use QuantNest or require a workspace subscription or Private installation.']],
    ['Tools and extensions', ['Web applications, business dashboards, document and workflow automation, data processing, debugging, testing and reports.', 'Authorised code conversion and API integrations are quoted after a feasibility review. Projects involving financial advice, live broker execution or restricted data require a separate assessment before acceptance and activation.']],
    ['A scope you can review', ['Agree inputs, outputs, acceptance criteria, environments, ownership and third-party costs in writing.', 'Small tools typically start at ₹15,000–₹40,000. Larger testing applications or integrations start at ₹50,000–₹1.5 lakh+. These are scope-dependent quotation starting points, not fixed prices.']],
    ['Enquiries through support', ['Send your custom development requirement and receive replies through Support.', 'Project scope, agreements, payments, delivery and ongoing project communication are handled separately, outside this platform.']],
    ['Support after handover', ['Choose optional maintenance, updates and a defined support allowance.', 'Your agreement identifies deliverables, source-code handover and ownership or licence rights. Any pre-existing components and third-party dependencies are identified separately.']],
  ], cta: 'Tell us what you want to build', kind: 'custom' },
  about: { title: 'Make the reasoning visible.', description: 'QuantNest is an independently developed platform for people who want to understand, test and improve their own trading process.', sections: [
    ['Why QuantNest exists', ['A result is easier to understand when you can inspect its rules and assumptions.', 'Research, configuration, testing, simulation and review belong to one connected investigation.']],
    ['What we believe', ['Your decisions should stay yours. Software should make them easier to inspect without promising a financial outcome.', 'Saved versions, visible costs and clear simulation boundaries help you ask better questions.']],
    ['Our initial focus', ['Supported NSE cash-stock workflows for self-directed users in India.', 'Separate custom software projects are available to discuss. Private is not currently offered to customers. Additional markets and instruments need separate development and verification.']],
  ] },
  trust: { title: 'Clear expectations from the beginning.', description: 'Understand what the software does, how your work is handled and which decisions remain yours.', sections: [
    ['Your logic and decisions', ['You choose instruments, rules, sizing and cost assumptions.', 'QuantNest provides software, not investment advice, managed trading, trading signals or assured returns.']],
    ['Results with context', ['Review observation times, costs, coverage and assumptions alongside results.', 'AI answers link to supporting evidence where available. Check the evidence before relying on an explanation.']],
    ['Account and privacy controls', ['Use two-factor authentication and sign-in session controls.', 'Private notes and execution records are not part of public strategy links. Product update emails require a separate subscription.']],
    ['Commercial clarity', ['Review plan limits and checkout totals before paying. Public plans do not activate Live.', 'Custom projects use written agreements. Private is not available for purchase. Contact us to clarify your requirements.']],
  ] },
  'privacy-policy': { title: 'Privacy notice', description: 'Revision 17 October 2026. What information supports your service and how to manage your choices.', sections: [
    ['Information supporting your workspace', ['Account details, sign-in information, saved rules, research questions, execution records, reviews, support messages and billing records support the features you use.', 'Keep passwords, broker secrets and authentication cookies out of support forms and AI questions.']],
    ['Service providers and AI processing', ['Configured providers include Oracle for hosting and protected storage, Cloudflare for delivery/protection, Brevo for email and Razorpay for payments. Google sign-in is used when selected.', 'AI research may send questions and attached context to the configured Gemini service. Content-free application error categories are recorded in service logs.']],
    ['Email and browser storage', ['Email supports account security, billing and replies to your support requests.', 'Browser storage supports sign-in and preferences such as your theme. We do not track product usage or website visits, or record session replays.']],
    ['Access, export and deletion', ['Use account settings or support for export or deletion requests. Execution must be safely settled before deletion.', 'Billing and audit records may need retention for applicable obligations. Contact us about your specific request.']],
    ['Questions and revisions', ['Contact the published support address for privacy questions or grievances.', 'Material changes to this notice are versioned and published here.']],
  ] },
  'terms-of-service': { title: 'Workspace terms', description: 'Public subscription scope, your responsibilities and the limits of simulated results.', sections: [
    ['Service scope', ['Research, configuration, historical testing, simulation and review software for your own logic.', 'Public plans cover the supported workflow through Paper. Custom projects have separate agreements. Customer Private deployments and Live trading are not currently available.']],
    ['Responsible use', ['The initial public offering is for adult India-resident users and supported NSE cash stocks.', 'Use authorised accounts and content and comply with applicable requirements. This is not discretionary management of customer trading accounts.']],
    ['Plans and billing', ['Explore is free. The pricing page shows the current Build and Pro prices and allowances. Checkout shows the reviewed total including applicable taxes.', 'No rollover or automatic paid overages. Automatic renewal requires consent.']],
    ['Cancellation and expiry', ['Cancel future renewal while keeping the paid period. Plan changes are scheduled at renewal.', 'Saved work remains accessible; further activity must fit current limits. Resuming Paper is an explicit action.']],
    ['Result limitations', ['AI may be incorrect. Backtests and simulation depend on observations, costs and assumptions.', 'Results do not establish future profitability or reproduce every broker/exchange condition.']],
    ['Custom project contracts', ['Separate agreements define deliverables, acceptance, ownership, confidentiality, payments, handover and maintenance.', 'Projects involving regulated activities or broker execution require separate assessment. Required permissions must be established before the relevant functionality is activated.']],
    ['Refunds and support', ['The first paid Workspace purchase has a seven-day refund window alongside applicable remedies.', 'Use Billing and Usage or the published support channel. Custom project contracts have separate terms.']],
  ] },
  refunds: { title: 'Change your mind with a clear process.', description: 'Cancellation, the first-purchase refund window and the terms of custom work.', sections: [
    ['First paid Workspace purchase', ['Request a refund within seven days of your first paid Workspace purchase, alongside applicable remedies.', 'Submit a payment reference and reason in Billing and Usage. Track the request in your account.']],
    ['After your request', ['Requests are reviewed; payment-provider processing may take additional time.', 'Confirmed refunds link to the original payment. Status and relevant credit notes remain in your billing records.']],
    ['Cancel future renewal', ['Stop future automatic renewal while preserving the current paid period.', 'Saved work remains accessible. Further activity must fit your current allowances; no automatic paid overages apply.']],
    ['Custom work', ['Milestones, handover and maintenance have separately agreed cancellation/refund terms.', 'Review the written quote and contract before acceptance.']],
  ] },
  methodology: { title: 'Read the assumptions with the result.', description: 'Historical tests, simulated fills, costs and unavailable metrics explained.', sections: [
    ['Historical observations', ['Tests use available candles and your saved rules. Indicators may need earlier candles before values are usable.', 'Crossovers need a previous observation. Holidays, gaps and coverage affect calculations.']],
    ['Costs and fills', ['Choose a charge profile and slippage and inspect their effect on trades.', 'Candles do not reveal every movement or exchange queue. If stop and target both fall within a candle, the model uses its stated stop-first assumption.']],
    ['Terminal and Paper', ['Terminal simulates manual orders; Paper simulates automated execution of saved rules.', 'Neither establishes live broker fills. Broker partial fills and manual reductions are separate closes.']],
    ['Timing and coverage', ['Check timeframe and observation date. Completed candles and a current quote are different observations.', 'Missing history and unverified corporate-action adjustments can limit results. Availability depends on supported markets and your account.']],
    ['Unavailable metrics', ['Empty totals are zero; undefined ratios are N/A.', 'Recorded closes cannot supply historical equity metrics without the necessary series. Check remaining exposure and diagnostics too.']],
  ] },
  security: { title: 'Protect your workspace and your access.', description: 'Practical account controls and a clear way to report concerns.', sections: [
    ['Protect your account', ['Enable 2FA and keep recovery codes private.', 'Review sessions and revoke unfamiliar access. Keep credentials and cookies out of messages.']],
    ['Report a vulnerability', ['Choose Security report in Contact or email the published address.', 'Describe the page and reproduction steps without other people’s data. Do not run destructive production tests.']],
    ['Project responsibilities', ['Agree access, updates, backups and incident responsibilities for each custom project.', 'Support access is limited to the agreed work. Do not send secrets through enquiry forms.']],
    ['What to expect', ['Reports are triaged during published support hours.', 'Verified incidents are investigated and affected customers informed as appropriate. No 24/7 response or uptime SLA is implied.']],
  ] },
  changelog: { title: 'What you can use. What comes next.', description: 'Current capabilities and future work are presented separately.', sections: [
    ['Research and strategy development', ['Conversations, configurable screens, readable rules and version history.', 'Historical tests preserve settings and results; completed tests can be attached for research.']],
    ['Practice and review', ['Separate manual Terminal and automated Paper, with journal reviews and performance reports.', 'Account controls, usage, billing and support are connected to your workspace. Availability is shown in your account.']],
    ['Future development', ['Additional markets, instruments, integrations, imports and team workflows are future or separately scoped work.', 'They are not included as delivered public subscription capabilities. Share priorities through Feedback.']],
  ] },
};
