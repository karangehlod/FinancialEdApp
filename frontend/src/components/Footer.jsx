import React from 'react'
import { Wallet, Mail, Github, Twitter, Shield, FileText } from 'lucide-react'

/**
 * Footer — shown on public pages (Login, Register) and optionally in the app.
 * Displays owner/contact info, key features, and compliance links.
 * Follows production requirements for GDPR-compliant public-facing pages.
 */
export const Footer = () => (
  <footer className="w-full bg-gray-900 text-gray-300 py-10 px-6 mt-auto">
    <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">

      {/* Brand & Owner */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Wallet size={22} className="text-indigo-400" />
          <span className="text-xl font-bold text-white">FinEd</span>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          A personal finance platform to track expenses, manage budgets,
          set savings goals, and master your financial future.
        </p>
        <p className="text-xs text-gray-500">
          Built &amp; maintained by <span className="text-indigo-300 font-semibold">Karan Gehlod</span>
        </p>
      </div>

      {/* Features */}
      <div>
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
          Features
        </h3>
        <ul className="space-y-2 text-sm text-gray-400">
          <li>💸 Expense Tracking &amp; Categorisation</li>
          <li>📊 Monthly Budget Management</li>
          <li>🎯 Savings Goals</li>
          <li>🏦 Loan &amp; EMI Calculator</li>
          <li>📈 Financial Reports &amp; Analytics</li>
          <li>🔔 Smart Notifications &amp; Alerts</li>
          <li>🤖 AI-Powered Financial Chat</li>
          <li>🔐 Two-Factor Authentication (2FA)</li>
          <li>🇪🇺 GDPR Data Export &amp; Deletion</li>
        </ul>
      </div>

      {/* Contact & Legal */}
      <div>
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
          Contact &amp; Support
        </h3>
        <ul className="space-y-3 text-sm">
          <li>
            <a
              href="mailto:support+theprodsde@gmail.com"
              className="flex items-center gap-2 text-gray-400 hover:text-indigo-400 transition-colors"
            >
              <Mail size={15} />
              support+theprodsde@gmail.com
            </a>
          </li>
          <li>
            <a
              href="https://github.com/karangehlod"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-gray-400 hover:text-indigo-400 transition-colors"
            >
              <Github size={15} />
              github.com/karangehlod
            </a>
          </li>
          <li>
            <a
              href="https://twitter.com/karangehlod74m"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-gray-400 hover:text-indigo-400 transition-colors"
            >
              <Twitter size={15} />
              @karangehlod74m
            </a>
          </li>
        </ul>

        <div className="mt-6 space-y-2 text-xs text-gray-500">
          <a
            href="/privacy-policy"
            className="flex items-center gap-1 hover:text-indigo-400 transition-colors"
          >
            <Shield size={13} />
            Privacy Policy
          </a>
          <a
            href="/terms-of-service"
            className="flex items-center gap-1 hover:text-indigo-400 transition-colors"
          >
            <FileText size={13} />
            Terms of Service
          </a>
        </div>
      </div>
    </div>

    {/* Bottom Bar */}
    <div className="max-w-5xl mx-auto mt-8 pt-6 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-600">
      <p>© {new Date().getFullYear()} FinancialEdApp. All rights reserved.</p>
      <p>🔒 Your data is encrypted and never sold to third parties.</p>
    </div>
  </footer>
)
