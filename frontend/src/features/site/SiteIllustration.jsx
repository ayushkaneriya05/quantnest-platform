import PropTypes from 'prop-types';
import './illustrations/illustrations.css';
import { BacktestIllustration, BuilderIllustration, ControlsIllustration, JournalIllustration, PaperIllustration, ResearchIllustration, ScreenerIllustration, TerminalIllustration } from './illustrations/FeatureIllustrations';
import { AboutIllustration, DevelopmentIllustration, HomeIllustration, PrivateIllustration, ProductIllustration, ResearchIntroIllustration, SecurityIllustration, ToolkitIllustration, TrustIllustration } from './illustrations/PageIllustrations';

const illustrations = {
  home: HomeIllustration, product: ProductIllustration, toolkit: ToolkitIllustration,
  'research-intro': ResearchIntroIllustration, research: ResearchIllustration,
  screener: ScreenerIllustration, builder: BuilderIllustration, backtesting: BacktestIllustration,
  terminal: TerminalIllustration, paper: PaperIllustration, journal: JournalIllustration,
  controls: ControlsIllustration, private: PrivateIllustration, development: DevelopmentIllustration,
  about: AboutIllustration, trust: TrustIllustration, security: SecurityIllustration,
};

export default function SiteIllustration({ name }) {
  const Illustration = illustrations[name];
  if (!Illustration) throw new Error(`Unknown site illustration: ${name}`);
  return <Illustration />;
}
SiteIllustration.propTypes = { name: PropTypes.oneOf(Object.keys(illustrations)).isRequired };
