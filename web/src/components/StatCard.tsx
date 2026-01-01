import type { ReactNode } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  highlight?: boolean;
}

export function StatCard({ label, value, change, changeLabel, icon, highlight }: StatCardProps) {
  const getTrendIcon = () => {
    if (change === undefined) return null;
    if (change > 0) return <TrendingUp className="w-4 h-4" />;
    if (change < 0) return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (change === undefined) return 'text-white/40';
    if (change > 0) return 'text-green-400';
    if (change < 0) return 'text-red-400';
    return 'text-white/40';
  };

  return (
    <div className={`card p-6 ${highlight ? 'glow border-blue-500/30' : ''}`}>
      <div className="flex items-start justify-between">
        <div className="text-white/60 text-sm">{label}</div>
        {icon && <div className="text-blue-400">{icon}</div>}
      </div>
      <div className="text-3xl font-bold mt-2">{value}</div>
      {(change !== undefined || changeLabel) && (
        <div className={`flex items-center gap-1 text-sm mt-2 ${getTrendColor()}`}>
          {getTrendIcon()}
          <span>
            {change !== undefined && `${Math.abs(change)}`}
            {changeLabel && ` ${changeLabel}`}
          </span>
        </div>
      )}
    </div>
  );
}
