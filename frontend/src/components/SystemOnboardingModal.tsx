import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  Users,
  Package,
  FileText,
  Wallet,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  X,
  ExternalLink,
  type LucideIcon,
} from 'lucide-react';
import { useEscapeClose } from '../hooks/useEscapeClose';

export const SYSTEM_INTRO_KEY = 'simple_invoicing_intro_seen_v1';

type StepInfo = {
  id: string;
  number: number;
  title: string;
  tabLabel: string;
  icon: LucideIcon;
  tagline: string;
  whereIsIt: string;
  description: string[];
  tips?: string;
  actionLabel: string;
  actionPath: string;
};

const STEPS: StepInfo[] = [
  {
    id: 'company',
    number: 1,
    title: '1. Set up Company Profile & Branding',
    tabLabel: '1. Company',
    icon: Building2,
    tagline: 'Where your business name, address, GSTIN, and logo live',
    whereIsIt: 'Settings → Company Profile (/settings/company)',
    description: [
      'Enter your real Business Name (replace the default placeholder name so it represents your real company).',
      'Fill in your Address, State, GSTIN, and Phone Number.',
      'Upload your Company Logo (PNG or JPG). It will automatically appear at the top of every generated invoice PDF.',
      'Add your Bank Details and UPI ID so customers know where to send payments.',
      'Everything you configure here will print automatically on your invoices, receipts, and quotations.',
    ],
    tips: 'Important: Always scroll down and click "Save company" at the bottom of the page to apply your details.',
    actionLabel: 'Go to Company Setup',
    actionPath: '/settings/company',
  },
  {
    id: 'customers',
    number: 2,
    title: '2. Add your Customers (Ledgers)',
    tabLabel: '2. Customers',
    icon: Users,
    tagline: 'The people and businesses you sell to',
    whereIsIt: 'Sales → Ledgers (/ledgers/new) or directly inside Invoice composer',
    description: [
      'In Simple Invoicing, customer and supplier accounts are called "Ledgers".',
      'Add your customer’s Name, Phone number, and Billing Address.',
      'If your customer is registered for GST, enter their GSTIN. The app will automatically determine whether to charge CGST + SGST (intra-state) or IGST (inter-state).',
      'You can also quickly add a customer on-the-fly while typing an invoice by clicking "+ New ledger".',
    ],
    tips: 'Add your customer\'s phone number to send invoices and payment reminders via WhatsApp with one click.',
    actionLabel: 'Add a Customer',
    actionPath: '/ledgers/new',
  },
  {
    id: 'products',
    number: 3,
    title: '3. Add Products & Opening Stock',
    tabLabel: '3. Products',
    icon: Package,
    tagline: 'Items, goods, and services that you sell',
    whereIsIt: 'Catalogue → Products & Stock (/catalogue)',
    description: [
      'Add what you sell with its SKU code (e.g., ITEM-01), Unit Price, and applicable GST rate (e.g. 5%, 12%, 18%).',
      'Enter "Opening Stock" (how many units you currently have in inventory).',
      'For service-only businesses (like consulting or repairs), you can untick "Maintain inventory" to bill without stock limits.',
      'Every time you create an invoice, sold quantities are automatically deducted from your stock.',
    ],
    tips: 'Stock is updated in real-time, giving you accurate inventory warnings when quantities run low.',
    actionLabel: 'Open Catalogue',
    actionPath: '/catalogue',
  },
  {
    id: 'invoices',
    number: 4,
    title: '4. Create Sales Invoices',
    tabLabel: '4. Invoicing',
    icon: FileText,
    tagline: 'Make GST-ready tax invoices in seconds',
    whereIsIt: 'Sales → Invoices (/invoices)',
    description: [
      'Select "Sales" as the Voucher type.',
      'Choose your Customer from the dropdown list.',
      'Add line items from your product list, enter quantities, and add discounts if needed.',
      'Tax (CGST/SGST or IGST) and totals are calculated automatically according to Indian GST rules.',
      'Click "Create invoice" to save. The invoice number is generated, stock is reduced, and a PDF preview opens.',
      'You can print the PDF, download it, or share a direct link with your customer.',
    ],
    tips: 'You can generate multi-copy PDFs (Original for Recipient, Duplicate for Transporter, Triplicate for Supplier).',
    actionLabel: 'Create an Invoice',
    actionPath: '/invoices',
  },
  {
    id: 'cash-bank',
    number: 5,
    title: '5. Cash & Bank — How Payments Work',
    tabLabel: '5. Cash & Bank',
    icon: Wallet,
    tagline: 'Track money received, payments made, and live account balances',
    whereIsIt: 'Sales → Cash & Bank (/cash-bank)',
    description: [
      'When a customer pays an invoice, open the invoice and click "Record receipt" (or enter a receipt in Cash & Bank).',
      'Choose whether payment was received in Cash or deposited into your Bank account.',
      'The invoice status instantly updates to "Paid" (or "Partial"), and your Cash/Bank balance increases automatically.',
      'When you pay suppliers for purchase bills, recording a Payment marks the bill paid and deducts from your balance.',
      'Cash & Bank maintains an ongoing account ledger so your books always balance.',
    ],
    tips: 'Add your active bank accounts under Cash & Bank → Bank Accounts to display your account number and UPI QR on invoices.',
    actionLabel: 'Open Cash & Bank',
    actionPath: '/cash-bank',
  },
];

type SystemOnboardingModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export default function SystemOnboardingModal({ isOpen, onClose }: SystemOnboardingModalProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const navigate = useNavigate();
  const panelRef = useRef<HTMLDivElement>(null);

  useEscapeClose(onClose);

  useEffect(() => {
    if (isOpen) {
      panelRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const currentStep = STEPS[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === STEPS.length - 1;
  const StepIcon = currentStep.icon;

  const handleFinish = () => {
    try {
      localStorage.setItem(SYSTEM_INTRO_KEY, 'true');
    } catch {
      /* ignore */
    }
    onClose();
  };

  const handleAction = () => {
    try {
      localStorage.setItem(SYSTEM_INTRO_KEY, 'true');
    } catch {
      /* ignore */
    }
    onClose();
    navigate(currentStep.actionPath);
  };

  return (
    <div
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="system-guide-title"
      style={{ zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={onClose}
    >
      <div
        ref={panelRef}
        className="modal-panel"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '720px',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '12px',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-elevation-3)',
        }}
      >
        {/* Header */}
        <div
          className="panel__header"
          style={{
            padding: '20px 24px 16px',
            borderBottom: '1px solid var(--line-neutral)',
            background: 'var(--bg-panel)',
          }}
        >
          <div>
            <span
              style={{
                display: 'inline-block',
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                padding: '3px 8px',
                borderRadius: '4px',
                background: 'var(--color-primary-soft)',
                color: 'var(--color-primary)',
                marginBottom: '6px',
              }}
            >
              First-Time User Guide
            </span>
            <h2 id="system-guide-title" className="nav-panel__title" style={{ margin: 0, fontSize: '20px' }}>
              How Simple Invoicing Works
            </h2>
          </div>
          <button
            type="button"
            className="button button--ghost button--icon"
            onClick={onClose}
            title="Close guide"
            aria-label="Close guide"
          >
            <X size={18} />
          </button>
        </div>

        {/* Step Navigation Tabs */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--line-neutral)',
            background: 'var(--bg-card)',
            overflowX: 'auto',
          }}
        >
          {STEPS.map((step, idx) => {
            const active = idx === currentStepIndex;
            const completed = idx < currentStepIndex;
            return (
              <button
                key={step.id}
                type="button"
                onClick={() => setCurrentStepIndex(idx)}
                style={{
                  flex: 1,
                  minWidth: '110px',
                  padding: '12px 10px',
                  border: 'none',
                  background: active ? 'var(--bg-panel)' : 'transparent',
                  borderBottom: active ? '2px solid var(--color-primary)' : '2px solid transparent',
                  fontWeight: active ? 600 : 500,
                  fontSize: '13px',
                  color: active ? 'var(--color-primary)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease',
                }}
              >
                {completed ? (
                  <CheckCircle2 size={14} style={{ color: 'var(--color-success)' }} />
                ) : (
                  <span
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      background: active ? 'var(--color-primary)' : 'var(--line-neutral-strong)',
                      color: 'var(--text-on-accent)',
                      fontSize: '10px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                    }}
                  >
                    {step.number}
                  </span>
                )}
                {step.tabLabel}
              </button>
            );
          })}
        </div>

        {/* Body Content */}
        <div
          style={{
            padding: '24px',
            overflowY: 'auto',
            flex: 1,
            background: 'var(--bg-panel)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'var(--color-primary-soft)',
                color: 'var(--color-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <StepIcon size={24} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--text-main)' }}>
                {currentStep.title}
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                {currentStep.tagline}
              </p>
            </div>
          </div>

          <div
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              background: 'var(--bg-card)',
              border: '1px solid var(--line-neutral)',
              fontSize: '12px',
              color: 'var(--text-main)',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <strong>📍 Location:</strong> {currentStep.whereIsIt}
          </div>

          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
              How it works:
            </h4>
            <ul style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {currentStep.description.map((item, i) => (
                <li key={i} style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-main)' }}>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {currentStep.tips && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: '8px',
                background: 'var(--bg-accent)',
                border: '1px solid var(--line-neutral)',
                fontSize: '13px',
                lineHeight: '1.5',
                color: 'var(--text-main)',
                marginBottom: '16px',
              }}
            >
              💡 <strong>Tip:</strong> {currentStep.tips}
            </div>
          )}

          <div style={{ marginTop: '20px' }}>
            <button
              type="button"
              className="button button--secondary"
              onClick={handleAction}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}
            >
              <span>{currentStep.actionLabel}</span>
              <ExternalLink size={14} />
            </button>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid var(--line-neutral)',
            background: 'var(--bg-card)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Step {currentStepIndex + 1} of {STEPS.length}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              type="button"
              className="button button--ghost button--small"
              onClick={() => setCurrentStepIndex((prev) => Math.max(0, prev - 1))}
              disabled={isFirstStep}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            >
              <ChevronLeft size={16} />
              Previous
            </button>

            {isLastStep ? (
              <button
                type="button"
                className="button button--primary button--small"
                onClick={handleFinish}
              >
                Got it, let's start!
              </button>
            ) : (
              <button
                type="button"
                className="button button--primary button--small"
                onClick={() => setCurrentStepIndex((prev) => Math.min(STEPS.length - 1, prev + 1))}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
              >
                Next
                <ChevronRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
