import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import MainHeader from '@/shared/components/layout/main-header';

export default function TermsOfService() {
  return (
    <div className="relative flex h-dvh overflow-y-auto scrollbar-custom flex-col bg-card text-foreground">
      <div className="landing-market-animation absolute inset-0 opacity-70" />
      <div className="landing-grid absolute inset-0 opacity-25" />
      <MainHeader />
      
      <div className="relative flex min-h-0 flex-1 flex-col items-center px-4 pt-8 sm:pt-12">
        <Card className="w-full max-w-4xl shrink-0 overflow-hidden rounded-3xl border border-border bg-card/90 shadow-card backdrop-blur-xl">
          <CardHeader className="border-b border-border p-6 sm:p-8 bg-card/80">
            <CardTitle className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Terms of Service
            </CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">Last updated: {new Date().toLocaleDateString()}</p>
          </CardHeader>
          <CardContent className="p-6 sm:p-8 space-y-6 text-foreground leading-relaxed text-sm sm:text-base">
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-foreground">1. Acceptance of Terms</h2>
              <p>
                By accessing and using QuantNest ("the Platform"), you agree to be bound by these Terms of Service. If you do not agree to all the terms and conditions, you must not access or use the Platform. 
              </p>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-foreground">2. Platform Usage & Trading Risks</h2>
              <p>
                QuantNest provides algorithmic trading research, backtesting, paper trading, and live execution tools. You acknowledge that financial trading carries significant risk of capital loss.
              </p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Historical performance (backtesting) is not indicative of future results.</li>
                <li>Live trading execution involves technical risks, including slippage, latency, and API failures.</li>
                <li>QuantNest is a software provider, not a financial advisor. We do not provide investment advice.</li>
                <li>You are solely responsible for any financial losses incurred while using strategies developed or deployed via the Platform.</li>
              </ul>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-foreground">3. User Accounts & Security</h2>
              <p>
                You are responsible for maintaining the confidentiality of your account credentials, API keys, and Two-Factor Authentication (2FA) tokens. You agree to notify us immediately of any unauthorized access.
              </p>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-foreground">4. Intellectual Property</h2>
              <p>
                The strategies you create remain your intellectual property. However, by using the QuantNest Marketplace, you grant us the necessary licenses to display and distribute your strategies according to your configured pricing and permissions.
              </p>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-foreground">5. Service Availability</h2>
              <p>
                We strive to maintain 99.9% uptime, but we do not guarantee uninterrupted access to the Platform. We reserve the right to suspend or restrict access for maintenance or security purposes without prior notice.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-foreground">6. Termination</h2>
              <p>
                We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach these Terms.
              </p>
            </section>
          </CardContent>
        </Card>
        {/* Explicit bottom spacer to guarantee scroll gap */}
        <div className="h-8 sm:h-12 w-full shrink-0" />
      </div>
    </div>
  );
}
