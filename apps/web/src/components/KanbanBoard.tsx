import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Loader2, AlertCircle, CheckCircle2, RefreshCw, Play, RotateCcw, Trello } from 'lucide-react';
import { DashboardSnapshot, DashboardLane, DashboardWorkProduct, fetchBoardSnapshot, updateTaskStatus, startDashboard } from '../services/api';
import { TaskDetailModal } from './TaskDetailModal';

const POLL_INTERVAL_MS = 60000; // 60 seconds
const STATUS_COLUMNS = ['NOT_STARTED', 'IN_PROGRESS', 'AWAITING_REVIEW', 'COMPLETED'];
const STATUS_LABELS: Record<string, string> = {
  NOT_STARTED: 'Not Started',
  IN_PROGRESS: 'In Progress',
  AWAITING_REVIEW: 'Awaiting Review',
  COMPLETED: 'Completed',
};

const STATUS_COLORS: Record<string, { bg: string; border: string; icon: React.ReactNode }> = {
  NOT_STARTED: { bg: 'bg-slate-500/10', border: 'border-slate-500/30', icon: <Clock className="w-4 h-4 text-slate-400" /> },
  IN_PROGRESS: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" /> },
  AWAITING_REVIEW: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', icon: <AlertCircle className="w-4 h-4 text-amber-400" /> },
  COMPLETED: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" /> },
};

interface KanbanBoardProps {
  sessionId?: string;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({ sessionId: initialSessionId }) => {
  const [live, setLive] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId || null);
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [selectedTask, setSelectedTask] = useState<{ lane: DashboardLane; task: DashboardWorkProduct } | null>(null);
  const [draggedTask, setDraggedTask] = useState<{ laneKey: string; taskKey: string } | null>(null);
  const [draggedFrom, setDraggedFrom] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const pollRef = useRef<number | null>(null);

  // Poll for updates
  useEffect(() => {
    if (!sessionId) return;

    const poll = async () => {
      setIsLoading(true);
      try {
        const data = await fetchBoardSnapshot(sessionId);
        setSnapshot(data);
        setLastRefresh(new Date());
      } catch (e) {
        console.error('Failed to fetch board snapshot', e);
      } finally {
        setIsLoading(false);
      }
    };

    poll();
    pollRef.current = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => { if (pollRef.current) window.clearInterval(pollRef.current); };
  }, [sessionId]);

  const handleStart = async () => {
    setIsStarting(true);
    try {
      const { session_id } = await startDashboard(live);
      setSessionId(session_id);
    } finally {
      setIsStarting(false);
    }
  };

  const handleReset = () => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    setSessionId(null);
    setSnapshot(null);
    setSelectedTask(null);
    setLastRefresh(null);
  };

  const handleTaskDragStart = (laneKey: string, taskKey: string, e: React.DragEvent) => {
    setDraggedTask({ laneKey, taskKey });
    setDraggedFrom(null);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleTaskDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleTaskDrop = async (status: string, e: React.DragEvent) => {
    e.preventDefault();
    if (!draggedTask || !sessionId) return;

    setDraggedFrom(draggedTask.laneKey);
    try {
      await updateTaskStatus(sessionId, draggedTask.taskKey, status);
      // Refresh snapshot
      const data = await fetchBoardSnapshot(sessionId);
      setSnapshot(data);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Failed to update task status', err);
    }
    setDraggedTask(null);
    setDraggedFrom(null);
  };

  const formatTimeAgo = (date: Date | null) => {
    if (!date) return 'never';
    const diffMs = Date.now() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    if (diffSecs < 60) return 'just now';
    const diffMins = Math.floor(diffSecs / 60);
    return `${diffMins}m ago`;
  };

  if (!sessionId) {
    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/4 pointer-events-none" />
        <div className="relative z-10 space-y-4">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-300 text-xs font-bold border border-indigo-500/20 uppercase tracking-widest">
            <Trello className="w-3.5 h-3.5" /><span>Kanban Board</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Customer Payments Data Product</h2>
          <p className="text-slate-400 text-sm max-w-2xl">
            Matrix view of every agent's work products (plus a Human Review lane) across the delivery
            workflow — drag a card between columns to update its status. DEMO mode replays the same
            fully scripted simulation as the Project Dashboard; LIVE mode tracks real AgentCore
            Harness / GitHub Copilot agent runs.
          </p>
          <div className="flex items-center gap-3 pt-2">
            <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-700 rounded-xl p-1">
              <button onClick={() => setLive(false)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${!live ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>DEMO</button>
              <button onClick={() => setLive(true)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${live ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>LIVE</button>
            </div>
            <button onClick={handleStart} disabled={isStarting}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold flex items-center gap-2 transition">
              {isStarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isStarting ? 'Starting…' : 'Start Board'}
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  if (!snapshot) {
    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-3xl flex items-center justify-center h-96">
        <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
      </motion.div>
    );
  }

  // Prepare lanes including Human Review
  const lanesList = snapshot.lanes;
  const humanReviewTasks = lanesList
    .flatMap(lane => lane.work_products.filter(wp => wp.status === 'AWAITING_REVIEW'))
    .map(task => ({ ...task, _originLane: lanesList.find(l => l.work_products.some(wp => wp.key === task.key))?.key }));

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6 rounded-3xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-2xl font-extrabold text-white tracking-tight">{snapshot.title} — Kanban</h2>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                snapshot.live
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}>
                {snapshot.live ? 'LIVE' : 'DEMO'}
              </span>
            </div>
            <p className="text-slate-500 text-sm mt-1">Drag tasks across columns to update status</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <RefreshCw className="w-3 h-3" />
              Last refreshed {formatTimeAgo(lastRefresh)}
            </div>
            <button
              onClick={() => sessionId && fetchBoardSnapshot(sessionId).then(d => {
                setSnapshot(d);
                setLastRefresh(new Date());
              })}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition">
              Refresh Now
            </button>
            <button onClick={handleReset}
              className="px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition">
              <RotateCcw className="w-3.5 h-3.5" /> Reset
            </button>
          </div>
        </div>
      </motion.div>

      {/* Kanban Grid */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        className="glass-panel p-6 rounded-3xl overflow-x-auto">
        <div className="inline-block min-w-full">
          <div className="grid gap-4" style={{ gridTemplateColumns: '200px repeat(4, 1fr)' }}>
            {/* Header Row */}
            <div className="font-bold text-slate-400 text-xs uppercase tracking-wider pt-2">Lane</div>
            {STATUS_COLUMNS.map(status => (
              <div key={status} className="text-center">
                <div className={`rounded-xl p-3 ${STATUS_COLORS[status].bg} border ${STATUS_COLORS[status].border}`}>
                  <div className="flex items-center justify-center gap-1.5 mb-1">
                    {STATUS_COLORS[status].icon}
                    <span className="font-bold text-xs text-white uppercase tracking-wider">{STATUS_LABELS[status]}</span>
                  </div>
                </div>
              </div>
            ))}

            {/* Agent Lanes */}
            {lanesList.map(lane => (
              <React.Fragment key={lane.key}>
                <div className="flex items-start gap-2 pt-2 font-semibold text-xs">
                  <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${
                    lane.color === 'blue' ? 'bg-blue-500' :
                    lane.color === 'emerald' ? 'bg-emerald-500' :
                    lane.color === 'violet' ? 'bg-violet-500' :
                    'bg-orange-500'
                  }`} />
                  <div>
                    <div className="text-slate-200 truncate">{lane.name}</div>
                    <div className="text-[10px] text-slate-500">{lane.counts.done}/{lane.counts.total}</div>
                  </div>
                </div>

                {STATUS_COLUMNS.map(status => {
                  const tasksInCell = lane.work_products.filter(wp => wp.status === status);
                  return (
                    <div
                      key={`${lane.key}-${status}`}
                      onDragOver={handleTaskDragOver}
                      onDrop={(e) => handleTaskDrop(status, e)}
                      className={`rounded-lg p-3 min-h-[400px] transition-colors ${
                        draggedTask && draggedFrom === lane.key
                          ? 'bg-slate-800/50 border border-dashed border-slate-600'
                          : 'bg-slate-900/30 border border-slate-800/30'
                      }`}>
                      <div className="space-y-2">
                        {tasksInCell.map(task => (
                          <TaskCard
                            key={task.key}
                            task={task}
                            lane={lane}
                            onDragStart={(e) => handleTaskDragStart(lane.key, task.key, e)}
                            onClick={() => setSelectedTask({ lane, task })}
                            isDragging={draggedTask?.taskKey === task.key}
                          />
                        ))}
                        {tasksInCell.length === 0 && (
                          <div className="h-20 rounded-lg bg-slate-900/50 border border-dashed border-slate-700 flex items-center justify-center">
                            <span className="text-xs text-slate-600">No tasks</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </React.Fragment>
            ))}

            {/* Human Review Lane */}
            <div className="flex items-start gap-2 pt-2 font-semibold text-xs">
              <div className="w-2 h-2 rounded-full mt-1 flex-shrink-0 bg-gray-500" />
              <div>
                <div className="text-slate-200">Human Review</div>
                <div className="text-[10px] text-slate-500">{humanReviewTasks.length} pending</div>
              </div>
            </div>

            {/* Human Review Lane only shows AWAITING_REVIEW, rest empty */}
            {STATUS_COLUMNS.map(status => {
              const tasksInCell = status === 'AWAITING_REVIEW' ? humanReviewTasks : [];
              return (
                <div
                  key={`human-review-${status}`}
                  onDragOver={handleTaskDragOver}
                  onDrop={(e) => handleTaskDrop(status, e)}
                  className={`rounded-lg p-3 min-h-[400px] transition-colors ${
                    draggedTask
                      ? 'bg-slate-800/50 border border-dashed border-slate-600'
                      : 'bg-slate-900/30 border border-slate-800/30'
                  }`}>
                  <div className="space-y-2">
                    {tasksInCell.map(task => {
                      const originLane = snapshot.lanes.find(l => l.key === task._originLane);
                      return (
                        <TaskCard
                          key={task.key}
                          task={task}
                          lane={originLane || lanesList[0]}
                          onDragStart={(e) => handleTaskDragStart(originLane?.key || '', task.key, e)}
                          onClick={() => originLane && setSelectedTask({ lane: originLane, task })}
                          isDragging={draggedTask?.taskKey === task.key}
                          showOriginLane={true}
                        />
                      );
                    })}
                    {tasksInCell.length === 0 && status === 'AWAITING_REVIEW' && (
                      <div className="h-20 rounded-lg bg-slate-900/50 border border-dashed border-slate-700 flex items-center justify-center">
                        <span className="text-xs text-slate-600">No tasks awaiting review</span>
                      </div>
                    )}
                    {status !== 'AWAITING_REVIEW' && (
                      <div className="h-20 rounded-lg bg-slate-900/50 border border-dashed border-slate-700 flex items-center justify-center">
                        <span className="text-xs text-slate-600">—</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>

      {/* Task Detail Modal */}
      <AnimatePresence>
        {selectedTask && (
          <TaskDetailModal
            task={selectedTask.task}
            lane={selectedTask.lane}
            sessionId={sessionId}
            onClose={() => setSelectedTask(null)}
            onTaskUpdated={() => {
              sessionId && fetchBoardSnapshot(sessionId).then(d => {
                setSnapshot(d);
                setLastRefresh(new Date());
              });
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

interface TaskCardProps {
  task: DashboardWorkProduct;
  lane: DashboardLane;
  onDragStart: (e: React.DragEvent) => void;
  onClick: () => void;
  isDragging: boolean;
  showOriginLane?: boolean;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, lane, onDragStart, onClick, isDragging, showOriginLane }) => {
  const statusMeta = STATUS_COLORS[task.status] || STATUS_COLORS.NOT_STARTED;

  return (
    <motion.div
      draggable
      onDragStartCapture={onDragStart}
      onClick={onClick}
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={`rounded-lg p-2.5 cursor-move transition-all hover:shadow-lg ${
        isDragging ? 'opacity-50 scale-95' : 'opacity-100 scale-100'
      } bg-slate-800 border border-slate-700 hover:border-indigo-500/50`}>
      <div className="space-y-1.5">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-semibold text-slate-200 truncate flex-1">{task.name}</p>
          <div className="flex-shrink-0">{statusMeta.icon}</div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-700 text-slate-400">
            {task.phase}
          </span>
          {showOriginLane && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-900/80 border border-slate-700 text-slate-300">
              {lane.name.split(' ')[0]}
            </span>
          )}
        </div>
        {task.updated_at && (
          <p className="text-[10px] text-slate-500">{new Date(task.updated_at).toLocaleString()}</p>
        )}
      </div>
    </motion.div>
  );
};
