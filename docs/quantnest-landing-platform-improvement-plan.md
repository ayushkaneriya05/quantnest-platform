# QuantNest Landing Page And Platform Website Improvement Plan

## Purpose

This document consolidates the full improvement direction for the QuantNest public website and landing experience. It combines the landing page redesign plan, professional software website requirements, and advanced platform-support features needed to make QuantNest feel like a serious trading software company, not only a polished application.

The goal is to improve the public-facing experience around the real product:

- AI research
- Strategy creation
- Strategy backtesting
- Paper strategy deployment
- Manual paper trading terminal
- Broker connections
- Live trading controls
- Risk management
- AI Engine
- Marketplace
- Journal and reports
- Learning, community, reputation, and governance

## Current State

The current landing page already has a strong foundation:

- Sticky shared header with dark/light support.
- Hero section with CTA buttons.
- Dashboard screenshot.
- Main workflow section.
- Platform features grid.
- Manual paper trading section.
- AI/Intelligence section.
- Ecosystem section.
- Final CTA.
- Footer disclaimer.

The shared header already supports:

- Logo.
- Navigation to landing sections.
- Theme toggle.
- Auth-aware dashboard/logout controls.
- Login/register CTAs.
- Mobile menu.

The current direction is visually strong, but the page can become more professional by improving trust, conversion paths, product specificity, legal/support infrastructure, and advanced company-level website features.

## Core Landing Page Improvements

### 1. Sharpen The Hero Positioning

The hero should explain QuantNest in five seconds.

Current direction:

> Build, test, and run trading strategies with confidence.

Recommended direction:

> Research with AI. Backtest your rules. Deploy to paper or live trading.

Alternative headline:

> Research, test, and deploy trading strategies from one workspace.

Recommended hero subtext:

> QuantNest helps traders turn ideas into rule-based strategies, backtest them on historical data, run them in paper trading, and move selected systems to live broker execution with risk controls.

Hero CTAs:

- Create your workspace
- View workflow
- Sign in, if secondary action is needed

Trust chips below hero:

- Paper-first testing
- Broker connections
- Risk controls
- No-code rule builder
- AI-assisted research

### 2. Upgrade Product Preview

The current single dashboard screenshot is useful, but a launch-ready trading platform should show multiple product moments.

Recommended preview elements:

- Main dashboard screenshot.
- Floating card: AI thesis generated.
- Floating card: Backtest completed.
- Floating card: Paper strategy running.
- Floating card: Risk limits active.
- Floating card: Emergency stop available.

The floating cards should remain outside the screenshot frame, slightly smaller, and subtle enough to feel premium.

### 3. Make The Core Workflow Dominant

The main workflow should be the strongest section of the landing page.

Recommended workflow:

1. Research with AI
   - Ask market questions.
   - Screen instruments.
   - Compare symbols.
   - Collect market context.

2. Build strategy rules
   - Configure entries.
   - Configure exits.
   - Set time windows.
   - Choose instruments.
   - Define position sizing.
   - Add stop-loss, targets, and risk rules.

3. Backtest
   - Run historical simulations.
   - Review trade-by-trade results.
   - Inspect equity curve and drawdown.
   - Analyze risk metrics.
   - Run Monte Carlo scenarios.

4. Deploy to paper trading
   - Run strategies in simulated capital.
   - Monitor positions and orders.
   - Review performance without real capital risk.

5. Connect broker and go live
   - Connect broker credentials.
   - Allocate capital.
   - Monitor live sessions.
   - Inspect execution logs.
   - Use emergency controls.

6. Review and improve
   - Use reports.
   - Journal decisions.
   - Review AI health scoring.
   - Track audit history.

Recommended UI:

- Desktop: horizontal pipeline.
- Mobile: vertical timeline.
- Add animated progress line, but keep it subtle.

### 4. Group Features By Product Area

The current feature grid is good, but all features currently feel too equal. A professional page should group features by user job.

Recommended sections:

#### AI Research

- AI Research Assistant.
- Market Screener.
- Alternative Data Hub.
- Market regime context.

User-friendly message:

> Find ideas worth testing before you build anything.

#### Strategy Studio

- Strategy list.
- Strategy wizard.
- Entry rules.
- Exit rules.
- Time rules.
- Asset routing.
- Risk settings.
- Auto-disable rules.
- Version history.
- Strategy review.
- Strategy permissions.

User-friendly message:

> Turn your trading idea into clear rules you can inspect and improve.

#### Backtesting Lab

- Backtest setup.
- Backtest results.
- Trade list.
- Equity/drawdown charts.
- Monte Carlo simulation.

User-friendly message:

> Understand how your strategy behaved before you put capital at risk.

#### Paper Trading

- Paper dashboard.
- Paper portfolio.
- Paper capital.
- Paper analytics.
- Paper order book.
- Paper positions.
- Paper trade history.

User-friendly message:

> Practice with simulated capital before moving to live trading.

#### Manual Paper Trading Terminal

This should remain clearly separate from strategy deployment.

Purpose:

> The trading terminal is for manual paper trading.

Capabilities:

- Watchlists.
- Instrument search.
- Live candles.
- Order ticket.
- Paper buy/sell orders.
- Account summary.
- Positions.
- Orders.
- Trade history.

Recommended title:

> Practice manual execution without risking real capital.

#### Live Trading And Brokers

- Broker connections.
- Broker charge profiles.
- Broker logs.
- Live portfolio.
- Live strategies.
- Execution logs.
- Emergency controls.

User-friendly message:

> Move selected strategies to live trading with broker connections, allocation controls, logs, and safeguards.

### 5. Improve AI Engine Section

The current “Intelligence” section is conceptually right, but it should be named and explained more directly.

Recommended title:

> AI Engine helps you review and improve strategies.

Feature cards:

- Strategy Advisor
- Strategy Health
- Market Regime
- Overfit Checks
- Risk Review

Important positioning:

> AI suggests. You decide.

Avoid implying that AI guarantees profit or replaces trading judgment.

### 6. Add Risk And Control Section

For a trading platform, risk controls should have their own strong section.

Include:

- Position sizing.
- Portfolio limits.
- Strategy auto-disable.
- Broker session monitoring.
- Live emergency stop.
- Execution logs.
- Audit history.
- Strategy approvals.

Recommended title:

> Controls designed for trading discipline.

Recommended message:

> QuantNest helps you define how much a strategy can trade, when it should stop, and how live execution can be monitored or paused.

### 7. Rebalance Ecosystem Section

The ecosystem is useful, but it should be visually secondary to the core trading workflow.

Keep:

- Marketplace.
- Journal and reports.
- Community.
- Learning center.
- Reputation/proofs/replays.
- Governance/compliance.

Recommended message:

> Tools for improving the trader, not only the trade.

### 8. Strengthen Final CTA

Recommended final CTA:

> Start with paper. Go live only when your process is ready.

CTA buttons:

- Create your workspace.
- Sign in.

Footer disclaimer should stay visible and serious.

## Header Improvement Plan

The current `main-header.jsx` is already solid. Recommended improvements:

### 1. Active Section State

Add active nav highlighting while scrolling.

Examples:

- Workflow active while user is in workflow section.
- Platform active while user is in product section.
- Intelligence active while user is in AI Engine section.
- Ecosystem active while user is in ecosystem section.

Implementation:

- Use `IntersectionObserver`.
- Add `aria-current="true"` on active nav item.

### 2. Theme Persistence

Current theme toggle should persist.

Add:

- Save selected theme in `localStorage`.
- Respect system preference on first visit.
- Avoid flash of wrong theme on load.

### 3. Auth-Aware CTAs

If logged in:

- Primary CTA should be `Open dashboard`.
- Avoid showing `Start building`.
- If user opens `/register`, redirect to dashboard.

If logged out:

- Show `Sign in`.
- Show `Start building`.

### 4. Mobile Menu Polish

Improve mobile menu:

- Close on route change.
- Close on Escape key.
- Add better full-width CTA block.
- Add focus management.
- Ensure theme button styles work in light mode.

### 5. Sticky Header Polish

Add:

- Slight shadow only after scrolling.
- Better backdrop blur.
- Optional compact height after scroll.

### 6. Logo Handling

Logo should work on both dark and light themes.

Recommended approach:

- Use theme-specific wordmarks if needed.
- Or place logo in a subtle container in light mode.
- Avoid relying on low-contrast gold text on light background.

## Professional Software Website Features

These are not main product features. They are supporting website/company features expected from serious software platforms.

### 1. SEO And Metadata

Add:

- Page title.
- Meta description.
- Open Graph title.
- Open Graph description.
- Open Graph image.
- Twitter/X card metadata.
- Canonical URL.
- Favicon and app icons.
- Sitemap.
- Robots.txt.
- JSON-LD structured data for SoftwareApplication / Organization.

### 2. Legal Pages

Required or strongly recommended:

- Privacy Policy.
- Terms of Service.
- Risk Disclosure.
- Trading Disclaimer.
- Cookie Policy.
- AI Disclaimer.
- Broker Integration Disclaimer.
- Simulated Performance Disclaimer.
- Data Sources Disclaimer.

For QuantNest, `Risk Disclosure` should be a separate page.

### 3. Professional Footer

Footer should include:

- Product links.
- Company links.
- Legal links.
- Contact/support.
- Social/community links, if used.
- Security page.
- Status page, if available.
- Copyright.
- Risk disclaimer.

### 4. Cookie Consent And Analytics Consent

If analytics, pixels, or marketing scripts are used:

- Show cookie banner.
- Allow accept/reject/manage preferences.
- Store consent.
- Disable analytics until consent is granted.
- Link to cookie policy.

### 5. Analytics Event Tracking

Track key interactions:

- Hero CTA clicked.
- Register CTA clicked.
- Sign in clicked.
- Theme toggled.
- Nav section clicked.
- Mobile menu opened.
- Footer legal link clicked.
- Demo/waitlist submitted.
- Pricing/plan CTA clicked.

Also capture:

- UTM source.
- UTM medium.
- UTM campaign.
- Referrer.
- First landing page.

### 6. Contact And Support

Add:

- Contact page.
- Support email.
- Sales/demo request form.
- Bug report link.
- Help center link.
- Expected response time.

### 7. FAQ Section

Add interactive FAQ accordion.

Functional requirements:

- Keyboard accessible.
- Deep-linkable FAQ items.
- Searchable later.
- FAQ schema for SEO.

Topics:

- What is paper trading?
- Is QuantNest investment advice?
- How does live trading work?
- Are broker credentials safe?
- What does AI Engine do?
- Can I manually trade?
- What exchanges/brokers are supported?
- What happens if a strategy fails?

### 8. Demo, Waitlist, Or Lead Capture

Not every visitor will register immediately.

Add one softer conversion path:

- Request demo.
- Join waitlist.
- Contact founder/team.
- Get launch updates.

Functional requirements:

- Email validation.
- Success/error states.
- Anti-spam protection.
- Backend endpoint or mailing integration.

### 9. Newsletter / Launch Updates

Add email capture for launch updates.

Requirements:

- Email input.
- Consent checkbox if needed.
- Success state.
- Error state.
- Rate limit or spam protection.

### 10. Status And Reliability

Trading users care about uptime.

Add:

- Status page link.
- Market data status later.
- Broker API status later.
- Maintenance banner system.
- Incident history later.

### 11. Security Page

Important for broker-connected software.

Explain:

- Broker credential handling.
- Encryption.
- 2FA.
- Session controls.
- Audit logs.
- Account deletion.
- Responsible disclosure contact.

### 12. Accessibility

Add:

- Skip-to-content link.
- Keyboard-accessible mobile menu.
- Escape key closes menu.
- Focus rings.
- Proper heading hierarchy.
- Good contrast in dark and light themes.
- Reduced motion support.
- Accessible accordion for FAQ.
- Correct alt text for screenshots.

### 13. Performance

Landing page should be fast.

Add:

- Optimized WebP/AVIF screenshots.
- Responsive image sizes.
- Preload logo and hero image.
- Lazy load below-fold images.
- Fixed image dimensions to avoid layout shift.
- Minimize animation cost.
- Respect `prefers-reduced-motion`.

### 14. Asset Fallbacks

Avoid broken visual states.

Add:

- Fallback text logo.
- Fallback dashboard preview card.
- Graceful image error handling.

### 15. Section Deep Links

Add:

- URL hash updates on section click.
- Direct loading to `/#workflow`, `/#platform`, etc.
- Active nav state while scrolling.

### 16. Pricing Or Access Section

Even if pricing is not final, users need access clarity.

Options:

- Private beta.
- Free launch workspace.
- Starter / Pro / Creator / Enterprise later.

Functional requirements:

- CTA per plan.
- Plan comparison later.

### 17. Changelog And Roadmap

Add:

- Public changelog.
- Public roadmap.
- “What’s new” page.

### 18. Feedback Widget

Useful during launch.

Add:

- Floating feedback button.
- Modal form.
- Categories: bug, feature request, broker request, pricing, confusion.
- Backend endpoint or email integration.

## Advanced Platform Website Features

These are higher-level features that make QuantNest feel like a mature platform.

### 1. Advanced Trust Features

Add:

- Public security page.
- Responsible disclosure form.
- Data retention explanation.
- Account deletion explanation.
- Audit/compliance page.
- How live trading safety works page.
- Incident/status history.

### 2. Advanced Conversion Features

Add:

- Interactive product tour.
- “Choose your workflow” selector:
  - I want to research.
  - I want to backtest.
  - I want paper trading.
  - I want live automation.
- Demo workspace preview without login.
- Role-based landing paths:
  - Discretionary trader.
  - System trader.
  - Algo creator.
  - Learner.
- Carefully worded time-saved calculator, avoiding profit promises.

### 3. Advanced Support Features

Add:

- Help center.
- Searchable documentation.
- Broker setup guides.
- Strategy building tutorials.
- Paper-to-live checklist.
- Onboarding checklist.
- Live chat or support widget later.

### 4. Advanced Product Marketing Pages

Create dedicated pages for:

- AI Research.
- Strategy Builder.
- Backtesting.
- Paper Trading.
- Manual Trading Terminal.
- Live Trading.
- Broker Integrations.
- Risk Controls.
- AI Engine.
- Marketplace.
- Security.

These pages improve SEO and help users understand one product area at a time.

### 5. Advanced Account Flow

Add:

- Continue where you left off CTA.
- Preserve intended destination after login.
- Workspace/team invite landing state.
- Referral links.
- Email verification reminder if logged in but unverified.

### 6. Advanced Compliance

Add:

- Risk profile gate before live trading.
- Simulated performance disclaimer.
- AI disclaimer.
- Broker/data provider disclaimer.
- Jurisdiction availability notice.
- Age/eligibility confirmation if required.
- Cookie/tracking preference center.

### 7. Advanced Analytics

Add:

- Funnel tracking from landing to register to first workspace.
- CTA A/B testing.
- Section engagement tracking.
- Heatmap support.
- UTM attribution through signup.
- Demo/waitlist conversion events.

### 8. Advanced Personalization

If logged in, landing/header can show:

- Open dashboard.
- Resume strategy.
- View paper account.
- Check live sessions.
- Review notifications.

Other personalization:

- Remember preferred theme.
- Remember preferred landing section.
- Show region-specific broker availability.
- Show beta/launch banner only to relevant users.

### 9. Advanced Visual Interaction

Add:

- Clickable dashboard mock/demo.
- Animated workflow simulation.
- Mini strategy builder preview.
- Mini backtest result preview.
- Live risk-control panel preview.
- Broker connection status preview.
- Before/after workflow comparison.

### 10. Advanced Reliability Features

Add:

- Status badge in footer/header.
- Market data status.
- Broker API status.
- Maintenance banner.
- Incident notification signup.
- Fallback UI when assets fail.

### 11. Advanced Community Features

Add public previews for:

- Strategy marketplace.
- Creator profile.
- Verified trade replay.
- Leaderboard.
- Learning paths.
- Community guidelines.

### 12. Advanced SEO

Add:

- Feature-specific pages.
- FAQ schema.
- Breadcrumb schema.
- SoftwareApplication schema.
- Organization schema.
- Optimized image alt text.
- Open Graph image per feature page.

## Recommended Implementation Priority

### Phase 1: Launch Essentials

High priority before public launch:

- SEO metadata.
- Open Graph/Twitter metadata.
- Sitemap and robots.txt.
- Footer legal links.
- Risk Disclosure page.
- Trading Disclaimer page.
- Contact/support page.
- Theme persistence.
- Auth-aware CTAs.
- Accessibility basics.
- Optimized images.
- Mobile menu polish.
- Header active section state.

### Phase 2: Professional Trust And Conversion

Add next:

- FAQ accordion.
- Security page.
- Broker integrations page.
- Request demo / waitlist form.
- Cookie consent if analytics is used.
- Analytics event wrapper.
- UTM capture.
- Section deep links.
- Asset fallbacks.

### Phase 3: Product-Led Growth

Add after core launch:

- Interactive workflow demo.
- Feature-specific landing pages.
- Help center.
- Broker setup guides.
- Public changelog.
- Public roadmap.
- Feedback widget.
- Pricing/access section.

### Phase 4: Advanced Platform Presence

Add once the platform matures:

- Status page.
- Market data/broker status.
- Incident history.
- Role-based landing paths.
- Personalized logged-in landing state.
- Public marketplace preview.
- Community/learning public previews.
- Advanced analytics and A/B testing.

## Highest-Value Additions For QuantNest

If prioritizing the strongest upgrades, focus on these:

1. Interactive workflow demo.
2. Security and Risk Disclosure pages.
3. Broker integrations page.
4. Waitlist/demo/contact form.
5. Feature-specific landing pages.
6. Auth-aware personalized CTAs.
7. Public changelog and roadmap.
8. Help center with broker and strategy guides.
9. UTM and analytics tracking.
10. Status page for market data and broker systems.

## Suggested Technical Tasks

### Landing Page

- Refactor content arrays into clearly named groups.
- Upgrade hero copy and CTA logic.
- Add product-led workflow section.
- Add risk/control section.
- Add grouped feature sections.
- Add interactive FAQ.
- Add lead capture block.
- Add optimized image handling.

### Header

- Add active section tracking.
- Add theme persistence.
- Add scroll shadow.
- Improve mobile menu behavior.
- Make CTA auth-aware.
- Add accessible keyboard handling.

### Routing

- Add routes for:
  - `/risk-disclosure`
  - `/trading-disclaimer`
  - `/security`
  - `/contact`
  - `/broker-integrations`
  - `/changelog`
  - `/roadmap`
  - `/help`

### Infrastructure

- Add SEO component.
- Add JSON-LD component.
- Add analytics utility.
- Add UTM capture utility.
- Add cookie consent manager.
- Add feedback/contact API integration.

## Final Direction

QuantNest should present itself as an end-to-end trading workflow platform:

> Research with AI, build rules, backtest, paper trade, connect brokers, go live with controls, and keep improving through reports and review.

The landing page should feel modern and premium, but the professional layer is what will create trust:

- Clear risk language.
- Strong security explanation.
- Real support paths.
- Legal pages.
- Product-specific demos.
- Accessibility and performance.
- Auth-aware user flow.
- Reliable company-level pages like roadmap, changelog, and status.

This combination will make QuantNest feel like a serious trading software company, not just a good-looking dashboard.
