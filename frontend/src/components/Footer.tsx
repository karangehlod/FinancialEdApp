/**
 * Footer — public-facing footer for Login, Register, and optionally in-app.
 * Displays brand info, features, contact, and legal links.
 * Responsive: stacks on mobile, 3-column grid on md+.
 * WCAG 2.1 AA: semantic HTML, proper link targets.
 */

import { memo } from 'react'
import { Wallet, Mail, Github, Twitter, Shield, FileText } from 'lucide-react'
import { FluidIcon } from '@/components/UI'

export const Footer = memo(function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="w-full bg-gray-900 text-gray-300 py-8 sm:py-10 px-4 sm:px-6 mt-auto">
      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Brand & Owner */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <FluidIcon icon={Wallet} size="md" className="text-indigo-400" />
            <span className="text-xl font-bold text-white">FinEd</span>
          </div>
          <p className="text-sm text-gray-400 mb-4">
            A personal finance platform to track expenses, manage budgets,
            set savings goals, and master your financial future.
          </p>
          <p className="text-xs text-gray-500">
            Built &amp; maintained by{' '}
            <span className="text-indigo-300 font-semibold">Karan Gehlod</span>
          </p>
        </div>

        {/* Contact & Legal (moved to take second column now that features removed) */}
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
            Contact &amp; Support
          </h3>
          <ul className="space-y-3 text-sm" aria-label="Contact links">
            <li>
              <a
                href="mailto:support+theprodsde@gmail.com"
                className="flex items-center gap-2 text-gray-400 hover:text-indigo-400 transition-colors"
              >
                <FluidIcon icon={Mail} size="sm" className="text-gray-400" />
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
                <FluidIcon icon={Github} size="sm" className="text-gray-400" />
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
                <FluidIcon icon={Twitter} size="sm" className="text-gray-400" />
                @karangehlod74m
              </a>
            </li>
          </ul>

          <div className="mt-6 space-y-2 text-xs text-gray-500">
            <a
              href="/privacy-policy"
              className="flex items-center gap-1 hover:text-indigo-400 transition-colors"
            >
              <FluidIcon icon={Shield} size="sm" className="text-gray-400" />
              Privacy Policy
            </a>
            <a
              href="/terms-of-service"
              className="flex items-center gap-1 hover:text-indigo-400 transition-colors"
            >
              <FluidIcon icon={FileText} size="sm" className="text-gray-400" />
              Terms of Service
            </a>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="max-w-5xl mx-auto mt-8 pt-6 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-600">
        <p>© {currentYear} FinancialEdApp. All rights reserved.</p>
        <p>🔒 Your data is encrypted and never sold to third parties.</p>
      </div>
    </footer>
  )
})

export default Footer
