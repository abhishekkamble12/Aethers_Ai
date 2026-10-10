import { ShieldCheck, Lock, Eye, FileText } from 'lucide-react';

export default function PrivacyPage() {
  return (
    <div className="container mx-auto px-4 md:px-6 py-12 max-w-4xl space-y-8">
      <div className="border-b border-slate-800 pb-6">
        <h1 className="text-3xl font-bold text-white tracking-tight">Privacy Policy</h1>
        <p className="text-sm text-slate-400 mt-2">
          Effective Date: October 2026. Saans (साँस) Air Safety & Compliance Infrastructure.
        </p>
      </div>

      <div className="space-y-6 text-sm text-slate-300 leading-relaxed">
        <section className="space-y-2">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-sky-400" />
            1. Data Minimization & Privacy Commitment
          </h2>
          <p>
            Saans operates under a strict data minimization paradigm. School day timetables, environmental sensor measurements, and regulatory GRAP Stage evaluation logs processed by our engine do not record or retain personal student identifiers.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Lock className="w-5 h-5 text-emerald-400" />
            2. Cryptographic Hashing & SHA-256 Ledger
          </h2>
          <p>
            All administrative schedule actions and verification receipts are converted into irreversible SHA-256 cryptographic hashes. Audit log blocks contain only canonical event metadata, timestamps, and actor role tags (e.g., principal:sch_481_delhi), ensuring immutable proof without exposing personal information.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Eye className="w-5 h-5 text-amber-400" />
            3. Notification Broadcasts
          </h2>
          <p>
            Parent advisories dispatched via WhatsApp and SMS are sent through encrypted gateway endpoints. Phone numbers are utilized solely for one-way advisory transmission during declared GRAP stages and are never sold or shared with third parties.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            4. Contact & Regulatory Inquiries
          </h2>
          <p>
            For compliance or privacy inquiries regarding Delhi-NCR educational district operations, contact our compliance team at privacy@saans.delhi.gov.in.
          </p>
        </section>
      </div>
    </div>
  );
}
