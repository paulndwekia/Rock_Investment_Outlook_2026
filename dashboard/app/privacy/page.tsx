export default function PrivacyPage() {
  return <main className="mx-auto max-w-3xl px-6 py-16 text-[#263139]">
    <a href="/" className="text-sm text-[#907342]">← Back to dashboard</a>
    <p className="mt-10 text-xs font-semibold uppercase tracking-[.18em] text-[#A08A5D]">Platform information</p>
    <h1 className="mt-3 text-3xl font-semibold tracking-tight">Privacy notice</h1>
    <p className="mt-3 text-sm leading-7 text-[#6F7975]">This notice describes the intended privacy approach for Kenya Investment Intelligence. It must be updated to match the services, analytics, authentication and hosting providers actually enabled before public launch.</p>
    <div className="mt-8 space-y-6 text-sm leading-7 text-[#57625F]">
      <section><h2 className="font-semibold text-[#263139]">Information handled</h2><p>The public research pages are designed to be readable without an account. If account, contact or administrative features are introduced, only information necessary for those functions should be collected and the purpose explained at the point of collection.</p></section>
      <section><h2 className="font-semibold text-[#263139]">Security and technical logs</h2><p>Hosting providers may process technical information such as request time, IP address, browser details and error logs for security and reliability. Access should be restricted and retention limited to what is necessary.</p></section>
      <section><h2 className="font-semibold text-[#263139]">Cookies</h2><p>Essential cookies may be used for security or account sessions if those features are enabled. Non-essential analytics or advertising cookies should not be enabled without the appropriate notice and consent where required.</p></section>
      <section><h2 className="font-semibold text-[#263139]">Data sources</h2><p>Market and economic records displayed on the platform are research data, not personal information about dashboard visitors. Source datasets remain subject to their applicable permissions and retention requirements.</p></section>
      <section><h2 className="font-semibold text-[#263139]">Your rights and contact</h2><p>Requests concerning personal information should be handled in accordance with applicable Kenyan data-protection law. A verified contact channel and controller details must be added before the public launch of any feature that collects personal information.</p></section>
    </div>
    <p className="mt-10 border-t border-[#E7E3DA] pt-5 text-xs text-[#929791]">Draft privacy notice. Add the responsible data controller, contact details, service providers, retention periods and request process after deployment configuration is confirmed.</p>
  </main>;
}