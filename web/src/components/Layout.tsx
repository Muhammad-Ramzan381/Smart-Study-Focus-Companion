import { Link, Outlet, useLocation } from 'react-router-dom';
import { Target, PlusCircle, History, BarChart3 } from 'lucide-react';

const navItems = [
  { path: '/', icon: BarChart3, label: 'Dashboard' },
  { path: '/session/new', icon: PlusCircle, label: 'New Session' },
  { path: '/history', icon: History, label: 'History' },
];

export function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen gradient-bg">
      {/* Navigation */}
      <nav className="border-b border-white/10 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="text-xl font-bold flex items-center gap-2 hover:opacity-80 transition">
            <Target className="w-6 h-6 text-blue-400" />
            <span>Study Companion</span>
          </Link>

          <div className="flex gap-1">
            {navItems.map(({ path, icon: Icon, label }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                  location.pathname === path
                    ? 'bg-blue-600 text-white'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 px-6 py-4 mt-auto">
        <div className="max-w-6xl mx-auto text-center text-white/40 text-sm">
          Smart Study & Focus Companion | Built with Purpose-Driven AI
        </div>
      </footer>
    </div>
  );
}
