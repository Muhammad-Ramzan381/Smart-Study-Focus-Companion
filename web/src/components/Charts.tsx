import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import type { DailyBreakdown, TopicAnalysis } from '../types';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const chartColors = [
  'rgba(59, 130, 246, 0.8)',   // blue
  'rgba(16, 185, 129, 0.8)',   // green
  'rgba(245, 158, 11, 0.8)',   // amber
  'rgba(239, 68, 68, 0.8)',    // red
  'rgba(139, 92, 246, 0.8)',   // purple
  'rgba(236, 72, 153, 0.8)',   // pink
];

interface DailyChartProps {
  data: DailyBreakdown[];
}

export function DailyChart({ data }: DailyChartProps) {
  const chartData = {
    labels: data.map(d => d.day),
    datasets: [
      {
        label: 'Minutes',
        data: data.map(d => d.minutes),
        backgroundColor: 'rgba(59, 130, 246, 0.7)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
        ticks: { color: 'rgba(255, 255, 255, 0.6)' },
      },
      x: {
        grid: { display: false },
        ticks: { color: 'rgba(255, 255, 255, 0.6)' },
      },
    },
  };

  return (
    <div className="h-[200px]">
      <Bar data={chartData} options={options} />
    </div>
  );
}

interface TopicChartProps {
  data: TopicAnalysis[];
}

export function TopicChart({ data }: TopicChartProps) {
  const chartData = {
    labels: data.map(t => t.topic),
    datasets: [
      {
        data: data.map(t => t.time),
        backgroundColor: chartColors.slice(0, data.length),
        borderWidth: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
        labels: {
          color: 'rgba(255, 255, 255, 0.8)',
          padding: 12,
          font: { size: 12 },
        },
      },
    },
  };

  if (data.length === 0) {
    return (
      <div className="h-[200px] flex items-center justify-center text-white/40">
        No topics yet
      </div>
    );
  }

  return (
    <div className="h-[200px]">
      <Doughnut data={chartData} options={options} />
    </div>
  );
}
