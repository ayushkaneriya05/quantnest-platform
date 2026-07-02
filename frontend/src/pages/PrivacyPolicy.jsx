import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import MainHeader from '@/shared/components/layout/main-header';

export default function PrivacyPolicy() {
  return (
    <div className="relative flex h-screen overflow-y-auto scrollbar-custom flex-col bg-[#050505] text-white">
      <div className="landing-market-animation absolute inset-0 opacity-70" />
      <div className="landing-grid absolute inset-0 opacity-25" />
      <MainHeader />
      
      <div className="relative flex min-h-0 flex-1 flex-col items-center px-4 pt-8 sm:pt-12">
        <Card className="w-full max-w-4xl shrink-0 overflow-hidden rounded-3xl border border-white/10 bg-[#0b0d12]/90 shadow-[0_28px_80px_rgba(0,0,0,0.55)] backdrop-blur-xl">
          <CardHeader className="border-b border-white/10 p-6 sm:p-8 bg-[#111318]/80">
            <CardTitle className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Privacy Policy
            </CardTitle>
            <p className="mt-2 text-sm text-slate-400">Last updated: {new Date().toLocaleDateString()}</p>
          </CardHeader>
          <CardContent className="p-6 sm:p-8 space-y-6 text-slate-300 leading-relaxed text-sm sm:text-base">
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-white">1. Information We Collect</h2>
              <p>
                At QuantNest, we collect information to provide better services to all our users. We collect information in the following ways:
              </p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Account Information:</strong> Name, email address, and encrypted passwords.</li>
                <li><strong>Financial Data:</strong> Paper trading balances and connected brokerage API keys (which are heavily encrypted and securely vaulted).</li>
                <li><strong>Strategy Data:</strong> Code, algorithms, and configurations for your trading bots.</li>
                <li><strong>Usage Data:</strong> Application logs, trade execution records, and session information.</li>
              </ul>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-white">2. How We Use Information</h2>
              <p>
                We use the information we collect from all of our services for the following purposes:
              </p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Provide, maintain, and improve our platform.</li>
                <li>Execute algorithmic trades on your behalf via connected brokerages.</li>
                <li>Process payments for subscription plans and marketplace purchases.</li>
                <li>Enhance system security and prevent abuse or unauthorized access.</li>
              </ul>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-white">3. Data Security & Encryption</h2>
              <p>
                We take security seriously. All sensitive data, including API keys and authentication tokens, are encrypted at rest using AES-256 and in transit via TLS 1.3. We strictly adhere to industry standards to protect your financial and algorithmic assets.
              </p>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-white">4. Sharing of Information</h2>
              <p>
                We do not sell your personal data or trading algorithms. We may share information with third-party service providers (such as hosting or payment processing) only to the extent necessary to provide our services. Your algorithms remain strictly confidential unless you explicitly choose to publish them in the Marketplace.
              </p>
            </section>
            
            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-white">5. Your Rights</h2>
              <p>
                You have the right to access, update, or delete your personal information. When you delete your account, all associated data, API keys, and algorithms are permanently removed from our active databases, though some aggregated logs may be retained for security compliance.
              </p>
            </section>

            <section className="space-y-3">
              <h2 className="text-xl font-semibold text-white">6. Contact Us</h2>
              <p>
                If you have any questions or concerns about this Privacy Policy, please contact our support team or reach out to the Data Protection Officer at privacy@quantnest.com.
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
