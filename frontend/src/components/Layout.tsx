import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { CircleHelp } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { NAV_SHORTCUTS, resolveDocumentTitle } from '../config/navigation';
import { useShortcuts } from '../context/ShortcutsContext';
import { useEscapeClose } from '../hooks/useEscapeClose';
import { isCheatSheetKey } from '../utils/keyboard';
import { useMarketplaceSync } from '../features/marketplace/useMarketplaceSync';
import { useSidebarStore } from '../store/useSidebarStore';
import Sidebar from './Sidebar';
import FeedbackDialog from './FeedbackDialog';
import FirstInvoiceTourCoach from './FirstInvoiceTourCoach';
import InvoiceCancelDialog from './InvoiceCancelDialog';
import ShortcutCheatSheet from './ShortcutCheatSheet';
import SystemOnboardingModal, { SYSTEM_INTRO_KEY } from './SystemOnboardingModal';
import ThemeToggle from './ThemeToggle';
import UpdateAvailableToast from './UpdateAvailableToast';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { registerAction, shortcutsMap } = useShortcuts();
  const navigate = useNavigate();
  const collapsed = useSidebarStore((state) => state.collapsed);

  // Mounted here rather than on the marketplace pages: the central server can
  // never reach a self-hosted instance, so orders only arrive while something
  // polls — and that has to keep happening wherever the user is in the app.
  useMarketplaceSync();

  // The mobile drawer is ephemeral; only the desktop rail persists.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  useEscapeClose(closeSidebar);

  useEffect(() => {
    const cleanups = NAV_SHORTCUTS.map(({ action, to }) =>
      registerAction(action, () => navigate(to)),
    );
    return () => cleanups.forEach(fn => fn());
  }, [registerAction, navigate]);

  const [cheatSheetOpen, setCheatSheetOpen] = useState(false);
  const closeCheatSheet = useCallback(() => setCheatSheetOpen(false), []);

  const [guideOpen, setGuideOpen] = useState(() => {
    try {
      return localStorage.getItem(SYSTEM_INTRO_KEY) !== 'true';
    } catch {
      return false;
    }
  });

  // Rendered outside the header: its backdrop-filter would trap the fixed overlay.
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.defaultPrevented || !isCheatSheetKey(e, Object.values(shortcutsMap))) return;
      // A dialog that is already open keeps the keyboard; this one included.
      if (document.querySelector('[aria-modal="true"]')) return;
      e.preventDefault();
      setCheatSheetOpen(true);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcutsMap]);

  useEffect(() => {
    document.title = `${resolveDocumentTitle(location.pathname)} | Simple Invoicing`;
  }, [location.pathname]);

  return (
    <div className={`app-shell${collapsed ? ' app-shell--rail' : ''}`}>
      <div className="app-shell__sidebar">
        <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />
      </div>
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}
      <div className="app-shell__main">
        <div className="app-shell__backdrop app-shell__backdrop--left" />
        <div className="app-shell__backdrop app-shell__backdrop--right" />
        <header className="page-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <span className="sidebar-toggle__bar" />
            <span className="sidebar-toggle__bar" />
            <span className="sidebar-toggle__bar" />
          </button>
          <div style={{ flex: 1 }} />
          <button
            type="button"
            className="button button--ghost button--small page-header__help"
            onClick={() => setGuideOpen(true)}
            aria-label="Open system guide"
            title="Open system guide"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', marginRight: '8px' }}
          >
            <CircleHelp size={16} aria-hidden="true" />
            <span className="page-header__help-label">System Guide</span>
          </button>
          <ThemeToggle />
        </header>

        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: 'easeOut' }}
          className="page-frame"
        >
          {children}
        </motion.main>
      </div>
      {cheatSheetOpen && <ShortcutCheatSheet onClose={closeCheatSheet} />}
      {feedbackOpen && <FeedbackDialog onClose={() => setFeedbackOpen(false)} />}
      <InvoiceCancelDialog />
      <UpdateAvailableToast />
      <FirstInvoiceTourCoach />
      <SystemOnboardingModal isOpen={guideOpen} onClose={() => setGuideOpen(false)} />
    </div>
  );
}
